# Control Loop — Email-Drafter

## Two Loops

**1. Polling loop** (background, scheduled)
```
check_emails task (every interval_minutes)
  → email_service.fetch_recent_emails(lookback_minutes, whitelist)
  → filter out seen_email_ids
  → for each new email:
      → post embed to Discord channel
      → create thread
      → initialize session state
      → prompt user: "yes / no?"
```

**2. Interaction loop** (event-driven, per thread message)
```
on_message (in tracked thread)
  → look up session by thread_id
  → dispatch by session["state"]:
      awaiting_decision  → _handle_decision()
      awaiting_context   → _handle_context() → AI draft
      draft_ready        → "approve" → _approve_draft()
                           else      → _refine_draft() → AI refine
```

## State Machine

```
awaiting_decision
    ├─ yes → awaiting_context
    └─ no  → [session deleted]

awaiting_context
    └─ <user context> → draft_ready

draft_ready
    ├─ approve → [Gmail draft saved, session deleted]
    └─ <feedback> → draft_ready (loop)
```

## Termination Conditions

- Session ends when user says "no" (skip) or "approve" (save draft)
- No max-iteration limit on the refine loop — user controls termination
- Polling loop runs indefinitely until bot shutdown

## Error Handling

| Error | Behavior |
|-------|----------|
| IMAP fetch failure | Log exception, optionally notify channel |
| AI call failure | Log exception, send error message in thread |
| Gmail draft save failure | Log exception, send error message in thread, session preserved |
