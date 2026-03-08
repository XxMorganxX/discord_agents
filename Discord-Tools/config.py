"""Bot configuration. Edit values below or use environment variables for secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_root = Path(__file__).resolve().parent
if (_root / ".env").exists():
    load_dotenv(_root / ".env")


# ── Edit these values or override via environment variables ───────────────────

DISCORD = {
    "command_prefix": "!",
    "channel_ids": [],  # Empty = all channels. Or e.g. [123456789, 987654321]
}

INFERENCE = {
    "url": "https://inference.stuart-labs.com",
    "timeout": 120,
}

MODEL = {
    "enable_thinking": True,
}

GENERATION = {
    "max_tokens": 512,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "repeat_penalty": 1.0,
}

CONVERSATION = {
    "max_history_messages": 10,
}

ERROR_SUMMARIZER = {
    "model": "gpt-5-nano",
    "max_completion_tokens": 30,
    "prompt": (
        "In one short sentence (max 15 words), explain this error to a non-technical user. "
        "Be specific about what failed. No jargon.\n\nError: {error}"
    ),
}


# ── BotConfig (built from above + env) ────────────────────────────────────────


@dataclass
class GenerationDefaults:
    max_tokens: int = 512
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    repeat_penalty: float = 1.0


@dataclass
class ErrorSummarizerConfig:
    model: str = "gpt-5-nano"
    max_completion_tokens: int = 30
    prompt: str = ERROR_SUMMARIZER["prompt"]


@dataclass
class BotConfig:
    discord_token: str = ""
    command_prefix: str = "!"
    channel_ids: list[int] = field(default_factory=list)
    inference_url: str = "https://inference.stuart-labs.com"
    inference_timeout: int = 120
    refresh_token: str = ""
    enable_thinking: bool = True
    generation: GenerationDefaults = field(default_factory=GenerationDefaults)
    max_history_messages: int = 10
    openai_api_key: str = ""
    error_summarizer: ErrorSummarizerConfig = field(default_factory=ErrorSummarizerConfig)


def load_config() -> BotConfig:
    """Build BotConfig from config values and environment variables."""
    channel_ids: list[int] = []
    env_channels = os.environ.get("DISCORD_CHANNEL_ID", "")
    if env_channels:
        for part in env_channels.split(","):
            part = part.strip()
            if part.isdigit():
                channel_ids.append(int(part))
    if not channel_ids:
        channel_ids = [int(c) for c in DISCORD.get("channel_ids", []) if str(c).isdigit()]

    gen = GENERATION
    generation = GenerationDefaults(
        max_tokens=int(gen.get("max_tokens", 512)),
        temperature=float(gen.get("temperature", 0.6)),
        top_p=float(gen.get("top_p", 0.95)),
        top_k=int(gen.get("top_k", 20)),
        min_p=float(gen.get("min_p", 0.0)),
        repeat_penalty=float(gen.get("repeat_penalty", 1.0)),
    )

    return BotConfig(
        discord_token=os.environ.get("DISCORD_TOKEN", ""),
        command_prefix=str(DISCORD.get("command_prefix", "!")),
        channel_ids=channel_ids,
        inference_url=str(INFERENCE.get("url", "https://inference.stuart-labs.com")).rstrip("/"),
        inference_timeout=int(INFERENCE.get("timeout", 120)),
        refresh_token=os.environ.get("INFERENCE_REFRESH_TOKEN", ""),
        enable_thinking=bool(MODEL.get("enable_thinking", True)),
        generation=generation,
        max_history_messages=int(CONVERSATION.get("max_history_messages", 10)),
    )
