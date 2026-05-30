from __future__ import annotations

from typing import Any

import httpx

from researchos.llm.client import (
    LLMConfigurationError,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
)


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        api_key: str,
        timeout_sec: float = 30.0,
        default_base_url: str = "https://api.openai.com/v1",
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = api_key
        self.timeout_sec = timeout_sec
        self.default_base_url = default_base_url.rstrip("/")
        self.transport = transport

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise LLMConfigurationError(
                "LLM API key is missing. Set RESEARCHOS_LLM_API_KEY or OPENAI_API_KEY."
            )
        if not request.profile.model:
            raise LLMConfigurationError(
                f"No model configured for role '{request.profile.role}'."
            )

        base_url = (request.profile.base_url or self.default_base_url).rstrip("/")
        payload: dict[str, Any] = {
            "model": request.profile.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            with httpx.Client(
                timeout=self.timeout_sec,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"LLM provider returned HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM provider request failed: {exc}") from exc

        data = response.json()
        return _parse_chat_completion_response(
            data,
            fallback_model=request.profile.model,
            fallback_provider=request.profile.provider,
        )


def _parse_chat_completion_response(
    data: dict[str, Any],
    fallback_model: str,
    fallback_provider: str,
) -> LLMResponse:
    choices = data.get("choices") or []
    if not choices:
        raise LLMProviderError("LLM provider response did not include choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise LLMProviderError("LLM provider response did not include message content.")

    usage = data.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)

    return LLMResponse(
        content=content,
        model=str(data.get("model") or fallback_model),
        provider=fallback_provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        dry_run=False,
    )
