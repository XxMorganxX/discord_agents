# Discord Bots Monorepo

Python monorepo containing two independent Discord bots and a shared launcher.

## Design Principle: Siloed Agents

Each subfolder is a fully independent, self-contained agent. They do **not** share code, configuration, secrets, environment variables, or state. Each bot has its own:

- `.env` file for secrets
- `requirements.txt` and (optionally) its own Python virtualenv
- Internal state (conversation history, seen email IDs, etc.) that lives only in-process
- Configuration module (`config.py`)

This isolation means each bot can be developed, deployed, and restarted independently without affecting the other.

## Bots

| Bot | Directory | Purpose |
|-----|-----------|---------|
| Discord Tools | `Discord-Tools/` | Forwards Discord messages to a local LLM inference server that executes tools (weather, Spotify, calendar, smart home, etc.) |
| Email Drafter | `Email-Drafter/` | Polls Gmail, posts emails to Discord threads, generates AI draft replies via OpenAI, and saves approved drafts back to Gmail |

## Quick Start

```bash
# Run both bots together
python run_all.py

# Or run individually
cd Discord-Tools && python bot.py
cd Email-Drafter && python main.py
```

`run_all.py` reads `bots.json` to discover each bot's entry point and spawns them as subprocesses. It handles graceful shutdown on SIGINT/SIGTERM.

## Setup

Each bot is set up independently — see the README in each subfolder:

- [`Discord-Tools/README.md`](Discord-Tools/README.md)
- [`Email-Drafter/README.md`](Email-Drafter/README.md)
