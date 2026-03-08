# Tool Registry — Email-Drafter

Email-Drafter does not use a model-driven tool registry. Its "tools" are direct service integrations called by the control loop at fixed points in the state machine.

## Actions (by role)

| Action | Module | Trigger |
|--------|--------|---------|
| Fetch recent emails | `email_service.fetch_recent_emails()` | Scheduled poll every N minutes |
| Post email embed to Discord | `discord_bot._handle_new_email()` | New unseen email found |
| Generate follow-up questions | `ai_service.generate_followup_questions()` | User replies "yes" to reply prompt |
| Generate draft reply | `ai_service.generate_draft_response()` | User provides reply context |
| Refine draft | `ai_service.refine_draft()` | User provides feedback on draft |
| Save draft to Gmail | `email_service.create_draft_reply()` | User types "approve" |

## Constraints

- Gmail fetch and draft creation happen over IMAP — requires app password, not account password
- AI calls are single-turn only; no chaining between actions
- No action can be called out of order — the state machine in `discord_bot.py` enforces sequencing
