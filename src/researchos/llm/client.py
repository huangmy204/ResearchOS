from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from researchos.models_router import ModelProfile

LLMMessageRole = Literal["system", "user", "assistant"]


class LLMMessage(BaseModel):
    role: LLMMessageRole
    content: str = Field(min_length=1)


class LLMRequest(BaseModel):
    profile: ModelProfile
    messages: list[LLMMessage]
    temperature: float = 0.0
    max_tokens: int | None = None


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    dry_run: bool = True


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a model completion for the request."""
