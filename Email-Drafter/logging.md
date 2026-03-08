# Logging Layer — Email-Drafter

## Destination

stdout via Python `logging`. Configured in `main.py`.

## Events Logged

| Event | Level | Fields |
|-------|-------|--------|
| Bot ready | INFO | username |
| Email fetch failure | EXCEPTION | full traceback |
| Follow-up question generation | INFO | output char count; DEBUG: model, max_tokens, prompt_len |
| Draft generation | INFO | output char count; DEBUG: model, max_tokens, prompt_len |
| Draft refinement | INFO | output char count; DEBUG: model, max_tokens, prompt_len |
| AI call complete | INFO | model, prompt_tokens, completion_tokens |
| AI call failure | EXCEPTION | full traceback |
| Gmail draft save failure | EXCEPTION | full traceback |
| Whitelist diagnostics | INFO | per-email match/no-match |

## Token Visibility

Token usage (prompt + completion) is logged at INFO level for every AI call via `ai_service._call()`.

## What Is Not Logged

- Full email body content
- Full draft text
- User messages in threads

## Debugging

1. Token counts in AI call logs show if prompts are unexpectedly large
2. `!checkdebug` command posts IMAP diagnostic output directly to Discord for email filtering issues
3. State machine transitions are not explicitly logged — add DEBUG logging in each `_handle_*` method if needed
