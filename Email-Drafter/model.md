# Model — Email-Drafter

## Provider

OpenAI `gpt-4o-mini` via the official Python SDK.

## Interface

`ai_service.py` is the provider boundary. `discord_bot.py` calls only three functions:
- `generate_followup_questions(sender, subject, body)`
- `generate_draft_response(sender, subject, body, user_context)`
- `refine_draft(current_draft, user_feedback)`

Swapping providers (e.g. to Claude or a local model) requires changing only `ai_service.py`.

## Parameters (config.py → AI_MODEL, AI_PARAMS)

| Operation           | Temperature | Max Tokens |
|--------------------|-------------|------------|
| followup_questions  | 0.5         | 150        |
| draft_response      | 0.7         | 1024       |
| refine_draft        | 0.7         | 1024       |

All parameters and all prompt templates live in `config.py → AI_PARAMS` and `config.py → PROMPTS`.

## Token Budget

Each call is single-turn. No multi-step agentic loop. Budget is enforced per call via `max_tokens`.
