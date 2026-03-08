"""HTTP client for the Tool Calling Mini inference API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import requests

from config import BotConfig
from .models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    GenerationParams,
    HealthResponse,
    TokenRequest,
    TokenResponse,
    ToolsResponse,
)


class APIError(Exception):
    """Base class for inference-API errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class AuthenticationError(APIError):
    """Raised on 403 -- invalid/expired API key or invalid refresh token."""


class InferenceClient:
    """Synchronous client for the inference API with rotating-key auth."""

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._base_url = config.inference_url.rstrip("/")

        self._api_key: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    def authenticate(self) -> TokenResponse:
        """Exchange the refresh token for a short-lived API key."""
        body = TokenRequest(refresh_token=self._config.refresh_token)

        resp = self._session.post(
            f"{self._base_url}/auth/token",
            json=body.model_dump(),
            timeout=min(self._config.inference_timeout, 10),
        )
        self._raise_for_status(resp)

        token = TokenResponse.model_validate(resp.json())
        self._api_key = token.api_key
        self._expires_at = token.expires_at
        return token

    @property
    def is_authenticated(self) -> bool:
        if self._api_key is None or self._expires_at is None:
            return False
        return datetime.now(timezone.utc) < self._expires_at

    def _ensure_valid_key(self) -> str:
        if not self.is_authenticated:
            self.authenticate()
        assert self._api_key is not None
        return self._api_key

    def _auth_header(self) -> dict[str, str]:
        return {"X-API-Key": self._ensure_valid_key()}

    def health(self) -> HealthResponse:
        """Check server and llama-server health (no auth required)."""
        resp = self._session.get(
            f"{self._base_url}/health",
            timeout=min(self._config.inference_timeout, 10),
        )
        self._raise_for_status(resp)
        return HealthResponse.model_validate(resp.json())

    def tools(self) -> ToolsResponse:
        """Fetch the list of available tools from the inference server."""
        resp = self._session.get(
            f"{self._base_url}/tools",
            headers=self._auth_header(),
            timeout=min(self._config.inference_timeout, 10),
        )
        self._raise_for_status(resp)
        return ToolsResponse.model_validate(resp.json())

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        enable_thinking: Optional[bool] = None,
        execute_tools: bool = True,
        generation: Optional[GenerationParams] = None,
    ) -> ChatResponse:
        """Send a conversation and receive a model response with tool execution."""
        if enable_thinking is None:
            enable_thinking = self._config.enable_thinking

        if generation is None:
            g = self._config.generation
            generation = GenerationParams(
                max_tokens=g.max_tokens,
                temperature=g.temperature,
                top_p=g.top_p,
                top_k=g.top_k,
                min_p=g.min_p,
                repeat_penalty=g.repeat_penalty,
            )

        request_body = ChatRequest(
            messages=messages,
            enable_thinking=enable_thinking,
            execute_tools=execute_tools,
            generation=generation,
        )
        payload = request_body.model_dump(exclude_none=True)

        resp = self._session.post(
            f"{self._base_url}/v1/chat/completions",
            json=payload,
            headers=self._auth_header(),
            timeout=self._config.inference_timeout,
        )

        if resp.status_code == 403:
            self._api_key = None
            resp = self._session.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=self._auth_header(),
                timeout=self._config.inference_timeout,
            )

        self._raise_for_status(resp)
        return ChatResponse.model_validate(resp.json())

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.ok:
            return

        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text

        if resp.status_code == 403:
            raise AuthenticationError(resp.status_code, detail)
        raise APIError(resp.status_code, detail)
