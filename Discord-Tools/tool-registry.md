# Tool Registry — Discord-Tools

## Ownership

Tools are defined, registered, and executed entirely on the inference server (`Tool-Calling-Mini/Model/tools/`). The Discord bot is a thin client — it does not own or dispatch tools directly.

## Tool List (current)

Fetched at runtime via `GET /tools`. As of last audit:

| Tool              | Description |
|-------------------|-------------|
| weather           | Hourly/daily forecast for current location |
| spotify_playback  | Play/pause, skip, volume, search, shuffle, repeat |
| kasa_lighting     | On/off and scene control for Kasa smart lights |
| calendar_data     | Read/create Google Calendar events |
| stickies          | Read/edit macOS Stickies app |
| send_sms          | Send iMessage to user's phone |
| google_search     | Web search (one call per request) |
| read_clipboard    | Read system clipboard contents |
| briefing          | Create/manage morning briefings |
| get_notifications | Check pending email summaries and news |
| system_info       | Internal assistant documentation |
| cursor_composer   | Send coding request to Cursor Composer |

## Dispatch

The model generates `<tool_call>` XML blocks. The server parses, validates, and executes them, then returns results in the `ChatResponse`. The bot never touches tool execution logic.

## Adding Tools

Add new tools to the inference server's `tool_calling_config.json` and implement the handler in `Model/tools/`. No bot changes required.
