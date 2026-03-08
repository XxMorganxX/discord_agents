# Memory System — Discord-Tools

## Current Strategy

Ephemeral only. No persistent memory across bot restarts.

Within a session, `ConversationManager` provides rolling short-term memory capped at `max_history_messages` (default 10 messages). This is state, not memory — it does not survive restarts.

## Implications

- Restarting the bot clears all conversation history across all channels
- There is no user preference storage, no episodic memory, no retrieval

## Future Considerations

If persistent memory is needed:
- Store `_history` per channel in a local SQLite or JSON file, keyed by `channel_id`
- Load on first message to a channel, flush after each turn
- The `ConversationManager` interface already encapsulates history access — adding persistence would require changes only inside that class
