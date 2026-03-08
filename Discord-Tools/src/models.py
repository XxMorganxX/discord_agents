"""Pydantic models for the inference API request/response schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    api_key: str
    expires_at: datetime


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class GenerationParams(BaseModel):
    max_tokens: Optional[int] = Field(None, ge=1)
    temperature: Optional[float] = Field(None, ge=0.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    min_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    repeat_penalty: Optional[float] = Field(None, ge=0.0)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    enable_thinking: Optional[bool] = True
    execute_tools: Optional[bool] = True
    generation: Optional[GenerationParams] = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class ToolResultResponse(BaseModel):
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float


class ChatResponse(BaseModel):
    content: str
    thinking: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_results: Optional[list[ToolResultResponse]] = None
    usage: Optional[Usage] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llama_server: Literal["reachable", "unreachable"]


class ToolsResponse(BaseModel):
    markdown: str
