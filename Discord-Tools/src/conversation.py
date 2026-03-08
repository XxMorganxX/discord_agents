"""Per-channel conversation manager with history truncation."""

from __future__ import annotations

from typing import Optional

from .inference_client import InferenceClient
from config import BotConfig
from .models import ChatMessage, ChatResponse, GenerationParams


class ConversationManager:
    """Maintains conversation history per channel and handles truncation."""

    def __init__(self, client: InferenceClient, config: BotConfig) -> None:
        self._client = client
        self._config = config
        self._history: list[ChatMessage] = []

    @property
    def history(self) -> list[ChatMessage]:
        return list(self._history)

    def send(
        self,
        user_message: str,
        *,
        generation: Optional[GenerationParams] = None,
    ) -> ChatResponse:
        """Send a user message and return the model's response with tool execution."""
        self._history.append(ChatMessage(role="user", content=user_message))
        self._truncate()

        response = self._client.chat(
            messages=self._history,
            enable_thinking=self._config.enable_thinking,
            execute_tools=True,
            generation=generation,
        )

        # Build assistant message including tool results for context
        assistant_content = response.content
        if response.tool_results:
            results_summary = "\n\n[Tool results]\n"
            for tr in response.tool_results:
                status = "✓" if tr.success else "✗"
                results_summary += f"- {tr.tool_name}: {status}\n"
                if tr.result:
                    results_summary += f"  {tr.result}\n"
                if tr.error:
                    results_summary += f"  Error: {tr.error}\n"
            assistant_content = (response.content or "").strip() + results_summary

        self._history.append(
            ChatMessage(role="assistant", content=assistant_content)
        )

        return response

    def clear(self) -> None:
        self._history.clear()

    def _truncate(self) -> None:
        max_msgs = self._config.max_history_messages
        if max_msgs <= 0 or len(self._history) <= max_msgs:
            return

        overflow = len(self._history) - max_msgs
        if overflow % 2 != 0:
            overflow += 1

        self._history = self._history[overflow:]
