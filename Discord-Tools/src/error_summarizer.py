"""Summarizes tool and API errors into short, readable messages using gpt-5-nano."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_client = None


def _get_client(api_key: str):
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key)
    return _client


def summarize_error(error: str, api_key: str, model: str, max_tokens: int, prompt_template: str) -> str:
    """Return a concise one-line summary of the error. Falls back to a truncated raw string on failure."""
    if not api_key:
        return error[:120]
    try:
        prompt = prompt_template.format(error=error[:600])
        resp = _get_client(api_key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Error summarizer failed: %s", e)
        return error[:120]
