import logging
import asyncio

import discord
from discord.ext import commands, tasks

import ai_service
import email_service
from config import ALLOW_DUPLICATE_POSTS, LOG_ALL_INCOMING, SCHEDULE, WHITELIST, get_env

log = logging.getLogger(__name__)


class EmailDrafterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.channel_id = int(get_env("DISCORD_CHANNEL_ID"))
        # thread_id -> session data
        self.sessions: dict[int, dict] = {}
        # track message_ids we've already posted to avoid duplicates across polls
        self.seen_email_ids: set[str] = set()

    async def setup_hook(self):
        await self._register_commands()
        self.check_emails.start()

    async def on_ready(self):
        log.info("Bot ready as %s", self.user)
        channel = self.get_channel(self.channel_id)
        if channel is not None:
            listing = "\n".join(f"• {addr}" for addr in WHITELIST)
            await channel.send(f"**Bot online — monitoring emails from:**\n{listing}")

    # ── Scheduled email polling ──────────────────────────────────────────

    @tasks.loop(minutes=5)
    async def check_emails(self):
        await self._do_check(notify_empty=False)

    async def _do_check(self, notify_empty: bool = False):
        channel = self.get_channel(self.channel_id)
        if channel is None:
            log.error("Could not find channel %s", self.channel_id)
            return

        try:
            emails = await asyncio.to_thread(
                email_service.fetch_recent_emails, SCHEDULE["lookback_minutes"], WHITELIST
            )
        except Exception:
            log.exception("Failed to fetch emails")
            if notify_empty:
                await channel.send("Failed to fetch emails.")
            return

        if ALLOW_DUPLICATE_POSTS:
            emails_to_post = emails
        else:
            emails_to_post = [e for e in emails if e["message_id"] not in self.seen_email_ids]

        if not emails_to_post:
            if notify_empty:
                await channel.send("No new emails found.")
            return

        for email in emails_to_post:
            if not ALLOW_DUPLICATE_POSTS:
                self.seen_email_ids.add(email["message_id"])

            if email["whitelisted"]:
                important = True
            else:
                important = await asyncio.to_thread(
                    ai_service.is_important,
                    email["sender"], email["subject"], email["body"],
                )

            if LOG_ALL_INCOMING:
                flag = "✅ important" if important else "⏭️ skipped"
                wl = " _(whitelisted)_" if email["whitelisted"] else ""
                await channel.send(
                    f"📬 **{email['subject']}** — from `{email['sender']}`\n"
                    f"› {flag}{wl}"
                )

            if important:
                await self._handle_new_email(channel, email)

    @check_emails.before_loop
    async def _wait_until_ready(self):
        await self.wait_until_ready()

    def _apply_interval(self):
        """Update the loop interval from config (called once at startup)."""
        self.check_emails.change_interval(minutes=SCHEDULE["interval_minutes"])

    # ── New email → Discord thread ───────────────────────────────────────

    async def _handle_new_email(self, channel: discord.TextChannel, email: dict):
        body_preview = email["body"][:1500] or "(empty body)"
        embed = discord.Embed(
            title=f"New email: {email['subject']}",
            description=body_preview,
            color=0x4A90D9,
        )
        embed.add_field(name="From", value=email["sender"], inline=False)

        msg = await channel.send(embed=embed)
        thread = await msg.create_thread(name=f"Re: {email['subject'][:90]}")

        self.sessions[thread.id] = {
            "email": email,
            "draft": None,
            "state": "awaiting_decision",
        }

        await thread.send("Would you like to reply to this email? (**yes** / **no**)")

    # ── Commands ─────────────────────────────────────────────────────────

    async def _register_commands(self):
        @self.command(name="list")
        async def list_whitelist(ctx: commands.Context):
            """Show the whitelisted sender addresses."""
            if ctx.channel.id != self.channel_id:
                return
            lines = ["**Whitelisted senders:**"] + [f"• {addr}" for addr in WHITELIST]
            await ctx.send("\n".join(lines))

        @self.command(name="check")
        async def force_check(ctx: commands.Context):
            """Manually trigger an email fetch right now."""
            if ctx.channel.id != self.channel_id:
                return
            await ctx.send("Checking for new emails...")
            await self._do_check(notify_empty=True)

        @self.command(name="checkdebug")
        async def check_debug(ctx: commands.Context):
            """Post whitelist matching diagnostics for recent inbox emails."""
            if ctx.channel.id != self.channel_id:
                return

            await ctx.send("Running whitelist diagnostics...")

            try:
                result = await asyncio.to_thread(
                    email_service.inspect_recent_emails, SCHEDULE["lookback_minutes"], WHITELIST
                )
            except Exception:
                log.exception("Failed to run whitelist diagnostics")
                await ctx.send("Failed to run diagnostics.")
                return

            checks = result["checks"]
            whitelist_text = ", ".join(WHITELIST)
            await ctx.send(f"Whitelist: `{whitelist_text}`")
            await ctx.send(
                f"Search: `SINCE {result['search_since']}` | "
                f"cutoff_est=`{result['cutoff_est']}` | "
                f"emails_matching_search=`{result['total_matching_search']}`"
            )
            if result.get("total_in_inbox") is not None and result["total_matching_search"] == 0:
                await ctx.send(f"Total emails in INBOX (ALL): `{result['total_in_inbox']}`")

            if not checks:
                if result.get("search_error"):
                    await ctx.send(f"IMAP search failed: status=`{result['search_status']}` error=`{result['search_error']}`")
                await ctx.send(
                    "No emails in the SINCE window. Either the inbox has no mail since that date, "
                    "or `GMAIL_ADDRESS` points to a different mailbox. Check that IMAP is enabled for the account."
                )
                return

            lines = []
            for item in checks:
                mark = "MATCH" if item["matched"] else "NO_MATCH"
                subject = item["subject"].replace("\n", " ").strip()
                if len(subject) > 60:
                    subject = subject[:57] + "..."
                lines.append(
                    f"[{mark}] in_window=`{item.get('in_time_window', False)}` "
                    f"parsed=`{item['parsed_email']}` from=`{item['from_raw']}` subject=`{subject}`"
                )

            chunk = ""
            for line in lines:
                if len(chunk) + len(line) + 1 > 1800:
                    await ctx.send(chunk)
                    chunk = line
                else:
                    chunk = f"{chunk}\n{line}" if chunk else line
            if chunk:
                await ctx.send(chunk)

    # ── User interaction in threads ──────────────────────────────────────

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Only handle messages inside tracked threads
        if not isinstance(message.channel, discord.Thread):
            await self.process_commands(message)
            return

        session = self.sessions.get(message.channel.id)
        if session is None:
            await self.process_commands(message)
            return

        content = message.content.strip()
        state = session.get("state", "draft_ready")

        if state == "awaiting_decision":
            await self._handle_decision(message.channel, session, content)
        elif state == "awaiting_context":
            await self._handle_context(message.channel, session, content)
        elif content.lower() == "approve":
            await self._approve_draft(message.channel, session)
        else:
            await self._refine_draft(message.channel, session, content)

    async def _handle_decision(self, thread: discord.Thread, session: dict, content: str):
        answer = content.lower()
        if answer in ("yes", "y"):
            email = session["email"]
            session["state"] = "awaiting_context"
            await thread.send("Great — let me figure out what I need to know.")
            try:
                questions = ai_service.generate_followup_questions(
                    email["sender"], email["subject"], email["body"]
                )
            except Exception:
                log.exception("Failed to generate follow-up questions")
                await thread.send("Something went wrong. Please describe what you'd like to say and I'll draft a reply.")
                return
            await thread.send(f"**Before I draft a reply, a few questions:**\n{questions}")
        elif answer in ("no", "n"):
            await thread.send("Got it — skipping this one.")
            del self.sessions[thread.id]
        else:
            await thread.send("Please reply with **yes** or **no**.")

    async def _handle_context(self, thread: discord.Thread, session: dict, context: str):
        email = session["email"]
        await thread.send("Drafting a reply based on your input...")
        try:
            draft_text = ai_service.generate_draft_response(
                email["sender"], email["subject"], email["body"], context
            )
        except Exception:
            log.exception("AI draft generation failed")
            await thread.send("Failed to generate a draft. Please try again.")
            return

        session["draft"] = draft_text
        session["state"] = "draft_ready"
        await thread.send(f"**Suggested reply:**\n>>> {draft_text}")
        await thread.send(
            "Reply here to refine the draft, or type **approve** to create the Gmail draft."
        )

    async def _refine_draft(self, thread: discord.Thread, session: dict, feedback: str):
        await thread.send("Refining draft...")
        try:
            new_draft = ai_service.refine_draft(session["draft"], feedback)
        except Exception:
            log.exception("AI refinement failed")
            await thread.send("Failed to refine the draft. Please try again.")
            return

        session["draft"] = new_draft
        await thread.send(f"**Updated draft:**\n>>> {new_draft}")
        await thread.send("Reply to refine further, or type **approve** to create the Gmail draft.")

    async def _approve_draft(self, thread: discord.Thread, session: dict):
        email = session["email"]
        try:
            email_service.create_draft_reply(
                thread_id=email["thread_id"],
                message_id=email["message_id"],
                to=email["sender_email"],
                subject=email["subject"],
                body=session["draft"],
            )
        except Exception:
            log.exception("Failed to create Gmail draft")
            await thread.send("Failed to create the Gmail draft. Please try again.")
            return

        await thread.send("Gmail draft created. You can find it in your Drafts folder.")
        del self.sessions[thread.id]


def create_bot() -> EmailDrafterBot:
    bot = EmailDrafterBot()
    bot._apply_interval()
    return bot