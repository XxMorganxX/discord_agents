# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python monorepo with two independent Discord bots and a shared launcher:
- **Discord-Tools** — Forwards messages to a local LLM inference server that executes tools (weather, Spotify, calendar, smart home, etc.)
- **Email-Drafter** — Polls Gmail every few minutes, posts emails to Discord threads, generates AI draft replies via OpenAI, and saves approved drafts back to Gmail

## Running the Bots

```bash
# Run both bots together (reads from bots.json)
python run_all.py

# Run individually
cd Discord-Tools && python bot.py
cd Email-Drafter && python main.py
```

## Installation

```bash
# Discord-Tools (no venv required)
cd Discord-Tools && pip install -r requirements.txt

# Email-Drafter (uses its own venv)
cd Email-Drafter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Email-Drafter's venv is already registered in `bots.json` — `run_all.py` uses `Email-Drafter/.venv/bin/python` for that bot automatically.

There are no test or lint commands configured.

## Architecture

### Discord-Tools

```
Discord message → bot.py → ConversationManager → InferenceClient
    → POST /v1/chat/completions (INFERENCE_URL)
    → ChatResponse (content + tool_results) → formatted Discord reply
```

- `bot.py` — Entry point; handles `!chat`, `!ask`, `!clear` commands and bare `!<message>` shorthand
- `config.py` — Defaults + `.env` overrides; `DISCORD_CHANNEL_ID` is comma-separated (empty = all channels)
- `src/conversation.py` — Per-channel `ConversationManager`; keeps last 10 messages; tool results are appended to assistant messages for context
- `src/inference_client.py` — Authenticated HTTP client; exchanges `INFERENCE_REFRESH_TOKEN` for a rotating API key via `POST /auth/token`
- `src/models.py` — Pydantic models for the inference API schema

### Email-Drafter

```
Scheduled task (every 3–5 min) → Gmail IMAP → filter by whitelist + deduplicate
    → Discord embed + thread → OpenAI draft → user feedback loop
    → save approved draft to [Gmail]/Drafts
```

- `main.py` — Validates env vars, creates and starts `EmailDrafterBot`
- `discord_bot.py` — Core bot class; `check_emails` async loop; per-thread session state in `self.sessions` dict; seen email IDs tracked in `self.seen_email_ids`
- `email_service.py` — IMAP4_SSL to `imap.gmail.com:993`; `fetch_recent_emails()` respects `lookback_minutes` window and sender whitelist; `create_draft()` sets `In-Reply-To`/`References` headers and saves to `[Gmail]/Drafts`
- `ai_service.py` — OpenAI `gpt-4o-mini` wrapper; `generate_draft_response()` for initial drafts, `refine_draft()` for user feedback iterations
- `config.py` — Whitelist comes from `EMAIL_WHITELIST` in `.env` (comma-separated); poll interval is 3 min; lookback window is 10 min

### Launcher

`run_all.py` reads `bots.json`, spawns each bot as a subprocess, and handles graceful shutdown (SIGINT/SIGTERM → terminate → timed kill).

## Environment Variables

**Discord-Tools** (`.env` in `Discord-Tools/`):
```
DISCORD_TOKEN=
DISCORD_CHANNEL_ID=          # comma-separated channel IDs; empty = all
INFERENCE_REFRESH_TOKEN=
```

**Email-Drafter** (`.env` in `Email-Drafter/`):
```
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=          # 16-char Gmail App Password (not account password)
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
OPENAI_API_KEY=
```

Both bots have `.env.example` files as templates.

## Key Design Decisions

- **Siloed agents** — Each subfolder is a fully independent agent. They share no code, configuration, secrets, environment variables, or state. Each bot has its own `.env`, `requirements.txt`, optional virtualenv, `config.py`, and in-process state. They can be developed, deployed, and restarted independently.
- **Discord-Tools** requires a running instance of the "Tool Calling Mini" inference server at the configured URL (`INFERENCE_URL` in `.env`, default: `http://localhost:8000`). The bot won't function without it.
- **Email-Drafter** requires Gmail IMAP to be enabled and an App Password (not the regular account password) because of Google's security requirements.
- State is in-memory only — restarting either bot clears conversation history (Discord-Tools) or the seen-email dedup set (Email-Drafter).
