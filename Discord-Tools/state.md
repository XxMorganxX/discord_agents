# State Store — Discord-Tools

## Shape

```python
conversations: dict[int, ConversationManager]  # keyed by channel_id
```

Each `ConversationManager` holds:
```python
_history: list[ChatMessage]  # role + content pairs
```

## Lifetime

In-memory only. Cleared on bot restart. Per-channel via `defaultdict` — each channel gets its own isolated conversation.

## Access

Only `ConversationManager.send()` reads and writes history. The bot's `on_message` handler calls `send()` and never touches `_history` directly.

## Truncation

After each user message is appended, `_truncate()` caps history at `max_history_messages` (default 10), always dropping pairs (user + assistant) to keep history coherent.

## Tool Results in State

After each assistant turn, tool results are appended as a summary block to the assistant message content before storing. This keeps tool context available in subsequent turns without a separate tool-message role.
