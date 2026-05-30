from __future__ import annotations

from datetime import UTC, datetime

from researchos.llm import LLMProviderError, LLMResponse
from researchos.models.run import ResearchDocument, ResearchRun
from researchos.models_router import ModelProfile
from researchos.planning import LLMResearchPlanner, StaticResearchPlanner


class JSONPlannerLLMClient:
    def __init__(self, content: str):
        self.content = content

    def complete(self, request):
        return LLMResponse(
            content=self.content,
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50,
            dry_run=False,
        )


class FailingPlannerLLMClient:
    def complete(self, request):
        raise LLMProviderError("planner unavailable")


def test_static_research_planner_returns_default_steps():
    plan = StaticResearchPlanner().plan(_run())

    assert [step["agent"] for step in plan] == ["planner", "searcher", "evidence_verifier"]
    assert plan[0]["step_id"] == "step_001"


def test_llm_research_planner_uses_structured_json_response():
    planner = LLMResearchPlanner(
        llm_client=JSONPlannerLLMClient(
            
                '{"steps":['
                '{"step_id":"step_001","goal":"Scope the question","agent":"planner",'
                '"expected_output":"scoped plan"},'
                '{"step_id":"step_002","goal":"Read local evidence","agent":"reader",'
                '"expected_output":"evidence notes"}'
                "]} "
            
        ),
        planner_profile=_profile(),
    )

    plan = planner.plan(_run())

    assert plan[0]["goal"] == "Scope the question"
    assert plan[1]["agent"] == "reader"


def test_llm_research_planner_falls_back_on_provider_error():
    planner = LLMResearchPlanner(
        llm_client=FailingPlannerLLMClient(),
        planner_profile=_profile(),
    )

    plan = planner.plan(_run())

    assert plan[0]["agent"] == "planner"
    assert plan[0]["planner_fallback_reason"] == "planner unavailable"


def _profile() -> ModelProfile:
    return ModelProfile(
        role="planner",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        provider="openai_compatible",
        configured=True,
    )


def _run() -> ResearchRun:
    return ResearchRun(
        run_id="run_test",
        session_id="session",
        status="planning",
        query="legal citation risk",
        documents=[
            ResearchDocument(
                title="Legal AI memo",
                text="Unsupported citations create legal research risk.",
            )
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
