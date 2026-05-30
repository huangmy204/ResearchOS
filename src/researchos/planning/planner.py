from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel, Field

from researchos.llm import LLMClient, LLMClientError, LLMMessage, LLMRequest
from researchos.models.run import ResearchRun
from researchos.models_router import ModelProfile


class PlanStep(BaseModel):
    step_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)


class PlanDraft(BaseModel):
    steps: list[PlanStep] = Field(min_length=1)


class ResearchPlanner(Protocol):
    def plan(self, run: ResearchRun) -> list[dict]:
        """Build a research plan for a run."""


class StaticResearchPlanner:
    def plan(self, run: ResearchRun) -> list[dict]:
        return _default_plan()


class LLMResearchPlanner:
    def __init__(
        self,
        *,
        llm_client: LLMClient,
        planner_profile: ModelProfile,
        fallback_planner: ResearchPlanner | None = None,
    ):
        self.llm_client = llm_client
        self.planner_profile = planner_profile
        self.fallback_planner = fallback_planner or StaticResearchPlanner()

    def plan(self, run: ResearchRun) -> list[dict]:
        try:
            response = self.llm_client.complete(
                LLMRequest(
                    profile=self.planner_profile,
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You are the planner for ResearchOS. "
                                "Return only compact JSON. Do not include markdown."
                            ),
                        ),
                        LLMMessage(role="user", content=self._build_prompt(run)),
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
            )
            draft = _parse_plan_draft(response.content)
        except (LLMClientError, ValueError) as exc:
            plan = self.fallback_planner.plan(run)
            plan[0]["planner_fallback_reason"] = str(exc)
            return plan

        return [step.model_dump(mode="json") for step in draft.steps]

    def _build_prompt(self, run: ResearchRun) -> str:
        document_titles = [document.title for document in run.documents]
        return "\n".join(
            [
                "Create a concise research plan for this run.",
                f"Research question: {run.query}",
                f"Available local documents: {document_titles or ['none']}",
                "",
                "Return JSON with this shape:",
                (
                    '{"steps":[{"step_id":"step_001","goal":"...","agent":"planner",'
                    '"expected_output":"..."}]}'
                ),
                "",
                "Use 3 to 5 steps. Prefer these agents when suitable:",
                "planner, searcher, reader, evidence_verifier, writer, reviewer",
            ]
        )


def _default_plan() -> list[dict]:
    return [
        {
            "step_id": "step_001",
            "goal": "Clarify the research question and define evidence requirements.",
            "agent": "planner",
            "expected_output": "research plan",
        },
        {
            "step_id": "step_002",
            "goal": "Collect initial sources for the query.",
            "agent": "searcher",
            "expected_output": "candidate source list",
        },
        {
            "step_id": "step_003",
            "goal": "Extract evidence spans and verify claim support.",
            "agent": "evidence_verifier",
            "expected_output": "evidence graph and report",
        },
    ]


def _parse_plan_draft(content: str) -> PlanDraft:
    raw = content.strip()
    if not raw:
        raise ValueError("LLM planner returned empty content.")

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM planner did not return valid JSON.") from exc

    return PlanDraft.model_validate(data)
