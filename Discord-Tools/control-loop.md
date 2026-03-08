# Control Loop — Discord-Tools

## Execution Flow

```
Discord message received (on_message)
  → is_allowed_channel() check
  → command prefix check
      → !clear / !tools → direct response, no model call
      → !<message> or bare message → send_to_inference()
          → ConversationManager.send(user_message)
              → append user message to history
              → truncate history if > max_history_messages
              → InferenceClient.chat(messages)
                  → POST /v1/chat/completions
                  → server: build prompt → llama-server → parse → execute tools → return
              → append assistant response + tool results to history
          → format_response() → edit placeholder message
```

## Termination Conditions

- Single-pass: one model call per user message. The server handles multi-step tool execution internally before returning.
- The bot does not implement retry loops or multi-turn agentic cycles.

## Error Handling

| Error | Behavior |
|-------|----------|
| APIError (non-HTML) | Edit placeholder with status code + detail |
| APIError (HTML body) | Edit placeholder with "inference server unreachable" |
| Uncaught exception | Edit placeholder with error string, log exception |

## Token Budget

Not enforced by the bot. Bounded indirectly by `max_history_messages` and the server's `max_tokens` parameter.
