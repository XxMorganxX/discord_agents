# State Store — Email-Drafter

## Shape

```python
# EmailDrafterBot instance fields
self.sessions: dict[int, dict]     # thread_id → session
self.seen_email_ids: set[str]      # message_ids already posted
```

### Session dict

```python
{
    "email": {
        "message_id": str,
        "thread_id": str,
        "sender": str,
        "sender_email": str,
        "subject": str,
        "body": str,
    },
    "draft": str | None,           # current draft text
    "state": str,                  # awaiting_decision | awaiting_context | draft_ready
}
```

## Lifetime

In-memory only. Both `sessions` and `seen_email_ids` reset on bot restart.

- `seen_email_ids` reset means already-posted emails may reappear after a restart if they fall within the `lookback_minutes` window
- `sessions` reset means any in-progress draft conversations are silently abandoned

## Access Patterns

- `sessions` is written by `_handle_new_email()` (create), `_handle_decision()` (delete on "no"), `_handle_context()` / `_refine_draft()` (update draft + state), `_approve_draft()` (delete)
- `seen_email_ids` is written by `_do_check()` and read on each poll cycle
- Only the bot's own methods access state — no external writers
