import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_here = Path(__file__).parent
_criteria_path = _here / "email_relevance_criteria.txt"
RELEVANCE_CRITERIA = _criteria_path.read_text(encoding="utf-8") if _criteria_path.exists() else ""

SCHEDULE = {
    "interval_minutes": 3,
    "lookback_minutes": 10,
}

WHITELIST = [
    "loganpros@gmail.com",
    "morgannstuart@gmail.com",
]

# When True, show all matching emails on each check, even if already posted.
# When False (default), only show emails that haven't been posted yet.
ALLOW_DUPLICATE_POSTS = False

# When True, post a one-line summary for every incoming email showing sender,
# subject, and whether it was flagged as important (before the whitelist/relevance
# filter decides whether to open a full thread).
LOG_ALL_INCOMING = True

# ── AI model parameters ───────────────────────────────────────────────────────

AI_MODEL = "gpt-4o-mini"
AI_RELEVANCE_MODEL = "gpt-5-nano"  # cheapest available; swap to gpt-4.1-nano when available

AI_PARAMS = {
    "relevance_check": {
        "max_tokens": 5,
    },
    "followup_questions": {
        "temperature": 0.5,
        "max_tokens": 150,
    },
    "draft_response": {
        "temperature": 0.7,
        "max_tokens": 1024,
    },
    "refine_draft": {
        "temperature": 0.7,
        "max_tokens": 1024,
    },
}

# ── Prompts ───────────────────────────────────────────────────────────────────

PROMPTS = {
    "relevance_check": (
        "You are an email importance filter. Reply with only the word IMPORTANT if this email "
        "requires the user's attention (personal, time-sensitive, actionable, or from a known contact). "
        "Otherwise reply with only the word SKIP. No other output.\n\n"
        "{relevance_criteria}"
        "From: {sender}\nSubject: {subject}\n\n{body}"
    ),
    "followup_questions": (
        "The user received this email and wants to reply. Ask 1-2 very brief questions "
        "(one line each, ~10 words max) to capture the gist of their reply. "
        "Output only the numbered questions.\n\n"
        "From: {sender}\nSubject: {subject}\n\n{body}"
    ),
    "draft_response": (
        "You are a helpful email assistant. Draft a professional and concise reply "
        "to the following email based on the user's instructions. "
        "Only output the reply body text, no subject line.\n\n"
        "From: {sender}\nSubject: {subject}\n\n{body}\n\n"
        "User's instructions for the reply:\n{user_context}"
    ),
    "refine_draft": (
        "You are a helpful email assistant. The user wants to adjust the following "
        "draft email reply based on their feedback. Return only the updated reply body.\n\n"
        "Current draft:\n{current_draft}\n\nUser feedback:\n{user_feedback}"
    ),
}


def get_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val
