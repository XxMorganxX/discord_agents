"""AI provider for the Email-Drafter bot.

All prompts and model parameters are defined in config.py.
This module is the only place that imports the OpenAI SDK —
swapping providers means changing only this file.
"""

import logging

from openai import OpenAI

from datetime import date

from config import AI_MODEL, AI_RELEVANCE_MODEL, AI_PARAMS, PROMPTS, RELEVANCE_CRITERIA, get_env

log = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_env("OPENAI_API_KEY"))
    return _client


def _call(prompt: str, params: dict) -> str:
    """Send a single-turn prompt to the AI model and return the text response."""
    log.debug("AI call | model=%s tokens=%s prompt_len=%d", AI_MODEL, params["max_tokens"], len(prompt))
    resp = _get_client().chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=params["temperature"],
        max_tokens=params["max_tokens"],
    )
    result = resp.choices[0].message.content.strip()
    usage = resp.usage
    log.info(
        "AI call complete | model=%s prompt_tokens=%d completion_tokens=%d",
        AI_MODEL,
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    return result


def is_important(sender: str, subject: str, body: str) -> bool:
    """Return True if the email passes the relevance filter. Uses the cheapest model."""
    criteria_block = f"{RELEVANCE_CRITERIA}\nToday's date: {date.today().isoformat()}\n\n"
    prompt = PROMPTS["relevance_check"].format(
        relevance_criteria=criteria_block,
        sender=sender,
        subject=subject,
        body=body[:500],
    )
    resp = _get_client().chat.completions.create(
        model=AI_RELEVANCE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=AI_PARAMS["relevance_check"]["max_tokens"],
    )
    verdict = resp.choices[0].message.content.strip().upper()
    log.info("Relevance check | sender=%s subject=%.40s verdict=%s", sender, subject, verdict)
    return verdict == "IMPORTANT"


def generate_followup_questions(sender: str, subject: str, body: str) -> str:
    prompt = PROMPTS["followup_questions"].format(sender=sender, subject=subject, body=body)
    return _call(prompt, AI_PARAMS["followup_questions"])


def generate_draft_response(sender: str, subject: str, body: str, user_context: str) -> str:
    prompt = PROMPTS["draft_response"].format(
        sender=sender, subject=subject, body=body, user_context=user_context
    )
    return _call(prompt, AI_PARAMS["draft_response"])


def refine_draft(current_draft: str, user_feedback: str) -> str:
    prompt = PROMPTS["refine_draft"].format(current_draft=current_draft, user_feedback=user_feedback)
    return _call(prompt, AI_PARAMS["refine_draft"])
