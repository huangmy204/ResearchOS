from __future__ import annotations

from researchos.llm.client import LLMRequest, LLMResponse


class MockLLMClient:
    def complete(self, request: LLMRequest) -> LLMResponse:
        prompt_text = "\n".join(message.content for message in request.messages)
        prompt_tokens = _rough_token_count(prompt_text)
        role = request.profile.role
        model = request.profile.model or f"mock-{role}-model"
        content = (
            f"[mock:{role}] This is a dry-run response. "
            "No external LLM API was called."
        )
        completion_tokens = _rough_token_count(content)
        return LLMResponse(
            content=content,
            model=model,
            provider=request.profile.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            dry_run=True,
        )


def _rough_token_count(text: str) -> int:
    if not text.strip():
        return 0
    return max(1, len(text.split()))
