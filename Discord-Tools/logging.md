# Logging Layer — Discord-Tools

## Destination

stdout via Python `logging.basicConfig`. Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

## Events Logged

| Event | Level | Fields |
|-------|-------|--------|
| Bot login | INFO | username, user id |
| Inference server health on startup | INFO | status, llama_server |
| Inference server unreachable | WARNING | exception message |
| Boot message send failure | WARNING | channel_id, exception |
| Incoming message forwarded to inference | INFO | author, channel, message preview (80 chars) |
| Inference complete | INFO | channel_id, prompt_tokens, completion_tokens, tokens/sec |
| API error | ERROR | status_code, detail (via placeholder edit) |
| Uncaught exception | EXCEPTION | full traceback |
| Tools fetch failure | EXCEPTION | full traceback |

## What Is Not Logged

- Full prompt content sent to the server
- Full model response content
- Per-tool call details (logged server-side)

## Debugging Non-Deterministic Behavior

1. Check token counts in "Inference complete" log lines — high prompt_tokens indicates context bloat
2. Check inference server logs for tool call details and llama-server output
3. Use `!clear` to reset history and reproduce with a fresh context
