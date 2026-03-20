# Discord Tools Bot

A Discord bot that forwards chat messages to the [Tool Calling Mini](https://github.com/your-org/Tool-Calling-Mini) inference API. The model analyzes requests, calls tools (weather, Spotify, calendar, etc.), and the bot returns the response with tool results.

## Prerequisites

- **Tool Calling Mini inference server** running (e.g. `python server.py` in `Model/`)
- **Discord bot token** from the [Discord Developer Portal](https://discord.com/developers/applications)

## Setup

1. **Clone and install dependencies**

   ```bash
   cd Discord-Tools
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Copy `.env.example` to `.env` and set:

   - `DISCORD_TOKEN` — your Discord bot token
   - `DISCORD_CHANNEL_ID` — channel ID(s) the bot will respond in (comma-separated for multiple; omit for all channels)
   - `INFERENCE_REFRESH_TOKEN` — same secret as your inference server's `INFERENCE_REFRESH_TOKEN`

3. **Optional:** Edit `config.py` to change the inference URL, command prefix, channel IDs, or generation settings.

## Running

1. Start the Tool Calling Mini inference server (in the `Model/` directory of that project).
2. Run the bot:

   ```bash
   python bot.py
   ```

## Usage

- **`!chat <message>`** or **`!ask <message>`** — Send a message to the assistant (e.g. `!chat What's the weather tomorrow?`)
- **`!<message>`** — Shorthand: `!Turn on the lights` sends "Turn on the lights" to the assistant
- **`!clear`** — Clear conversation history for the current channel
- **`!tools`** — List available tools on the inference server

The bot maintains separate conversation history per channel. The inference server executes tools (weather, Spotify, Kasa lights, calendar, etc.) and returns the results.

## Architecture

```
Discord message  →  bot.py  →  InferenceClient  →  POST /v1/chat/completions
                                                         ↓
                                              Tool Calling Mini server
                                              (runs tools, returns results)
                                                         ↓
Discord reply  ←  format_response  ←  ChatResponse (content + tool_results)
```

## Configuration

Edit `config.py` or use environment variables:

| Setting | In config.py | Env var |
|--------|--------------|---------|
| Channel IDs | `DISCORD["channel_ids"]` | `DISCORD_CHANNEL_ID` |
| Inference URL | `INFERENCE["url"]` | — |
| Timeout | `INFERENCE["timeout"]` | — |
| Command prefix | `DISCORD["command_prefix"]` | — |
| Max history | `CONVERSATION["max_history_messages"]` | — |
| OpenAI API key | — | `OPENAI_API_KEY` (optional; used for error summarization) |
