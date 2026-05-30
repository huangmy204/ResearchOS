from __future__ import annotations

from researchos.llm import LLMMessage, LLMRequest, MockLLMClient
from researchos.models_router import ModelProfile


def test_mock_llm_client_returns_dry_run_response_with_profile_metadata():
    client = MockLLMClient()
    request = LLMRequest(
        profile=ModelProfile(
            role="writer",
            model="writer-model",
            base_url="https://api.openai.com/v1",
            provider="openai",
            configured=True,
        ),
        messages=[
            LLMMessage(role="system", content="You write reports."),
            LLMMessage(role="user", content="Summarize the evidence."),
        ],
    )

    response = client.complete(request)

    assert response.dry_run is True
    assert response.model == "writer-model"
    assert response.provider == "openai"
    assert response.content.startswith("[mock:writer]")
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.total_tokens == response.prompt_tokens + response.completion_tokens


def test_mock_llm_client_uses_role_based_model_name_when_unconfigured():
    client = MockLLMClient()
    request = LLMRequest(
        profile=ModelProfile(role="planner", model="", provider="unconfigured"),
        messages=[LLMMessage(role="user", content="Plan a run.")],
    )

    response = client.complete(request)

    assert response.model == "mock-planner-model"
    assert response.provider == "unconfigured"
