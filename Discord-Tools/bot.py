"""Discord bot that forwards messages to the Tool Calling Mini inference API."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections import defaultdict

import discord
from discord.ext import commands

from config import load_config
from src.conversation import ConversationManager
from src.inference_client import APIError, InferenceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("discord-tools")


def format_response(response) -> str:
    """Format a ChatResponse for Discord (max 2000 chars per message)."""
    parts = []

    if response.content and response.content.strip():
        parts.append(response.content.strip())

    if response.tool_calls:
        parts.append("\n**Tool calls:**")
        for tc in response.tool_calls:
            args_str = json.dumps(tc.arguments, indent=2) if tc.arguments else "{}"
            parts.append(f"• `{tc.name}`: `{args_str[:200]}...`" if len(args_str) > 200 else f"• `{tc.name}`: `{args_str}`")

    if response.tool_results:
        parts.append("\n**Results:**")
        for tr in response.tool_results:
            status = "✓" if tr.success else "✗"
            parts.append(f"• {tr.tool_name}: {status}")
            if tr.result is not None:
                result_str = json.dumps(tr.result) if isinstance(tr.result, (dict, list)) else str(tr.result)
                if len(result_str) > 300:
                    result_str = result_str[:300] + "..."
                parts.append(f"  {result_str}")
            if tr.error:
                parts.append(f"  Error: {tr.error}")

    if response.usage:
        u = response.usage
        parts.append(f"\n_{u.prompt_tokens} prompt + {u.completion_tokens} completion tokens_")

    text = "\n".join(parts)
    if len(text) > 2000:
        text = text[:1997] + "..."
    return text or "_No response_"


def main() -> None:
    config = load_config()

    if not config.discord_token:
        logger.error("DISCORD_TOKEN is not set. Add it to .env or set the environment variable.")
        sys.exit(1)

    if not config.refresh_token:
        logger.error("INFERENCE_REFRESH_TOKEN is not set. Add it to .env or set the environment variable.")
        sys.exit(1)

    # Shared client for utility commands (tools, health)
    shared_client = InferenceClient(config)

    # Per-channel conversation managers
    conversations: dict[int, ConversationManager] = defaultdict(
        lambda: ConversationManager(InferenceClient(config), config)
    )

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=config.command_prefix,
        intents=intents,
        description="Tool-calling assistant powered by your local inference server",
    )

    @bot.event
    async def on_ready():
        logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
        try:
            client = InferenceClient(config)
            health = client.health()
            logger.info("Inference server: %s (llama: %s)", health.status, health.llama_server)
        except Exception as e:
            logger.warning("Could not reach inference server: %s", e)

        # Send boot message to configured channels (or first guild's first text channel if none configured)
        boot_msg = "**Tool-calling assistant online.** Use `!clear` to reset history, `!tools` to list available tools."
        if config.channel_ids:
            for ch_id in config.channel_ids:
                try:
                    ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                    await ch.send(boot_msg)
                except discord.DiscordException as e:
                    logger.warning("Could not send boot message to %s: %s", ch_id, e)
        else:
            for guild in bot.guilds:
                ch = guild.system_channel or next(
                    (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                    None,
                )
                if ch is not None:
                    try:
                        await ch.send(boot_msg)
                        break
                    except discord.DiscordException as e:
                        logger.warning("Could not send boot message: %s", e)

    @bot.command(name="clear")
    async def clear_history(ctx: commands.Context):
        """Clear conversation history for this channel."""
        channel_id = ctx.channel.id
        conversations[channel_id].clear()
        await ctx.reply("Conversation history cleared.")

    @bot.command(name="tools")
    async def list_tools(ctx: commands.Context):
        """List the tools available on the inference server."""
        try:
            result = await asyncio.to_thread(shared_client.tools)
            await ctx.reply(result.markdown)
        except APIError as e:
            await ctx.reply(f"Could not fetch tools ({e.status_code}): {e.detail}")
        except Exception as e:
            logger.exception("Error fetching tools")
            await ctx.reply(f"Error: {e}")

    def is_allowed_channel(channel_id: int) -> bool:
        if not config.channel_ids:
            return True
        return channel_id in config.channel_ids

    async def send_to_inference(message: discord.Message, user_message: str) -> None:
        manager = conversations[message.channel.id]
        placeholder = await message.reply("_Thinking..._")
        try:
            async with message.channel.typing():
                response = await asyncio.to_thread(manager.send, user_message)
            if response.usage:
                u = response.usage
                logger.info(
                    "Inference complete | channel=%s prompt_tokens=%d completion_tokens=%d tok/s=%.1f",
                    message.channel.id,
                    u.prompt_tokens,
                    u.completion_tokens,
                    u.tokens_per_second,
                )
            formatted = format_response(response)
            await placeholder.edit(content=formatted)
        except APIError as e:
            detail = str(e.detail).strip()
            if detail.startswith("<"):
                detail = "inference server is unreachable (Cloudflare/tunnel error)"
            elif len(detail) > 300:
                detail = detail[:300] + "..."
            await placeholder.edit(content=f"API error ({e.status_code}): {detail}")
        except Exception as e:
            logger.exception("Error processing message")
            await placeholder.edit(content=f"Error: {e}")

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        if not is_allowed_channel(message.channel.id):
            logger.debug("Ignoring message from channel %s (not in allowed list)", message.channel.id)
            return

        # Commands (!clear, !tools, etc.) take priority
        if message.content.startswith(config.command_prefix):
            ctx = await bot.get_context(message)
            if ctx.valid:
                await bot.invoke(ctx)
                return
            # Prefix but not a command — treat as chat (e.g. !what's the weather?)
            user_message = message.content[len(config.command_prefix) :].strip()
        else:
            user_message = message.content.strip()

        # Forward to the inference API
        if user_message:
            logger.info("Forwarding message from %s in #%s: %s", message.author, message.channel, user_message[:80])
            try:
                await send_to_inference(message, user_message)
            except Exception as e:
                logger.exception("Failed to send placeholder or start inference: %s", e)

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
