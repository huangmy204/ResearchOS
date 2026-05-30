from __future__ import annotations

import json

import httpx

from researchos.llm import LLMMessage, LLMRequest, MockLLMClient
from researchos.llm.openai_compatible import OpenAICompatibleLLMClient
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


def test_openai_compatible_client_posts_chat_completion_request():
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "model": "gpt-test",
                "choices": [{"message": {"content": "A concise model response."}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 5,
                    "total_tokens": 17,
                },
            },
        )

    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        timeout_sec=5,
        transport=httpx.MockTransport(handler),
    )
    request = LLMRequest(
        profile=ModelProfile(
            role="writer",
            model="gpt-test",
            base_url="https://llm.example.test/v1",
            provider="openai_compatible",
            configured=True,
        ),
        messages=[
            LLMMessage(role="system", content="You write reports."),
            LLMMessage(role="user", content="Summarize this."),
        ],
        temperature=0.2,
        max_tokens=128,
    )

    response = client.complete(request)

    assert captured_request is not None
    assert str(captured_request.url) == "https://llm.example.test/v1/chat/completions"
    assert captured_request.headers["Authorization"] == "Bearer test-key"
    payload = json.loads(captured_request.content)
    assert payload["model"] == "gpt-test"
    assert payload["messages"][0]["role"] == "system"
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 128
    assert response.content == "A concise model response."
    assert response.dry_run is False
    assert response.total_tokens == 17
