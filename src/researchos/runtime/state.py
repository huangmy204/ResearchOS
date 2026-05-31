from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun, RunStatus
from researchos.reporting import ReportDraft
from researchos.retrieval import RetrievedChunk


@dataclass
class WorkflowState:
    run: ResearchRun
    plan: list[dict] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    retrieved_chunk: RetrievedChunk | None = None
    sources: list[Source] = field(default_factory=list)
    source: Source | None = None
    evidence_items: list[Evidence] = field(default_factory=list)
    evidence: Evidence | None = None
    claims: list[Claim] = field(default_factory=list)
    claim: Claim | None = None
    verifications: list[CitationVerification] = field(default_factory=list)
    verification: CitationVerification | None = None
    report: ReportDraft | None = None


@dataclass(frozen=True)
class NodeResult:
    node_name: str
    status: RunStatus
    step_name: str
    completed_steps: int
    event_type: str
    payload: dict
    artifacts: list[str] = field(default_factory=list)


class WorkflowNode(Protocol):
    name: str

    def execute(self, state: WorkflowState) -> NodeResult:
        """Run one workflow node and mutate the workflow state."""
