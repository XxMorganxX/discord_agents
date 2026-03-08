# Email Drafter

A Discord bot that monitors a Gmail inbox for emails from whitelisted senders, generates AI-powered draft replies using OpenAI, and lets you refine and approve those drafts through Discord threads before saving them back to Gmail.

## How It Works

1. **Polls Gmail** on a configurable schedule, fetching recent emails from whitelisted senders via IMAP.
2. **Posts to Discord** — each new email appears as an embed in a designated channel, and a thread is created for it automatically.
3. **Generates a draft reply** using OpenAI (`gpt-4o-mini`) and posts it in the thread.
4. **Refine or approve** — reply in the thread with feedback to iterate on the draft, or type `approve` to save the final version as a Gmail draft.

## Project Structure

```
├── main.py            # Entry point — validates config and starts the bot
├── discord_bot.py     # Discord bot with scheduled email polling and thread management
├── email_service.py   # Gmail IMAP integration (fetch emails, create drafts)
├── ai_service.py      # OpenAI integration (generate and refine draft replies)
├── config.py          # Loads config.yaml and environment variables
├── config.yaml        # Operational settings (schedule, whitelist)
├── requirements.txt   # Python dependencies
└── .env               # Credentials (not committed)
```

## Setup

### Prerequisites

- Python 3.10+
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833)
- A [Discord bot token](https://discord.com/developers/applications) with the Message Content intent enabled
- An [OpenAI API key](https://platform.openai.com/api-keys)

### Installation

```bash
git clone <repo-url>
cd Email-Drafter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

**1. Environment variables** — copy the example and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your regular password) |
| `DISCORD_BOT_TOKEN` | Bot token from the Discord Developer Portal |
| `DISCORD_CHANNEL_ID` | ID of the Discord channel the bot should post in |
| `OPENAI_API_KEY` | OpenAI API key |

**2. `config.yaml`** — adjust operational settings:

```yaml
schedule:
  interval_minutes: 5    # How often to check for new emails
  lookback_minutes: 10   # How far back to search
whitelist:
  - sender@example.com   # Only emails from these addresses are processed
```

### Running

```bash
python main.py
```

## Usage

Once the bot is running and connected to Discord:

- New emails from whitelisted senders appear as embeds in the configured channel.
- Each email gets its own thread with an AI-generated draft reply.
- **Send a message** in the thread to give feedback — the draft will be refined accordingly.
- **Type `approve`** to save the current draft as a Gmail draft, ready to review and send from your inbox.

## Implementation Details

- **Email fetching** uses Python's `imaplib` to connect to `imap.gmail.com` over SSL. Emails are searched by date and filtered by sender against the whitelist. A `seen_email_ids` set prevents duplicate processing across polling cycles.
- **Draft creation** builds a proper MIME message with `In-Reply-To` and `References` headers so the draft threads correctly in Gmail, then appends it to the `[Gmail]/Drafts` folder via IMAP.
- **AI drafting** sends the original email body to OpenAI's chat completions endpoint with a system prompt instructing it to write a professional reply. Refinement passes include the current draft and user feedback.
- **Discord integration** uses `discord.ext.tasks` for scheduled polling and Discord threads for per-email conversations. Session state (original email + current draft) is stored in memory keyed by thread ID.

## Dependencies

| Package | Purpose |
|---|---|
| `discord.py` | Discord bot framework |
| `openai` | OpenAI API client |
| `pyyaml` | YAML config parsing |
| `python-dotenv` | `.env` file loading |
