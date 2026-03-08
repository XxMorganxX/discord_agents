# Memory System — Email-Drafter

## Current Strategy

Ephemeral only. No persistent memory across restarts.

Within a session, the draft and conversation state are stored in `self.sessions[thread_id]`. This survives for the lifetime of the bot process but not across restarts.

## Implications

- Restarting the bot clears all active draft sessions silently
- `seen_email_ids` resets, so emails from the lookback window may repost after a restart
- No user preference storage or history of past drafts

## Future Considerations

If persistence is needed:
- Serialize `seen_email_ids` to a local file on each update; load on startup — this prevents duplicate posts across restarts
- Optionally serialize active sessions to resume in-progress drafts after a restart
- Both are isolated to `discord_bot.py` — no other components would need changing
