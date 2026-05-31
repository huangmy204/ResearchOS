from __future__ import annotations

from datetime import UTC, datetime

from researchos.planning import ResearchPlanner, StaticResearchPlanner
from researchos.reporting import EvidenceReportWriter, ReportWriter
from researchos.retrieval import (
    LocalKeywordRetriever,
    NoopReranker,
    Reranker,
    Retriever,
    SourceDiversityPolicy,
)
from researchos.runtime.engine import SequentialWorkflowEngine, WorkflowCancelled, WorkflowEngine
from researchos.runtime.nodes import (
    EvaluationNode,
    EvidenceExtractionNode,
    PlanningNode,
    ReadingNode,
    ReportWritingNode,
    RetrievalNode,
    VerificationNode,
)
from researchos.runtime.state import WorkflowNode, WorkflowState
from researchos.stores.artifact_store import ArtifactStore
from researchos.stores.event_store import EventStore
from researchos.stores.run_store import RunStore
from researchos.verification import CitationVerifier, RuleBasedCitationVerifier


class ResearchWorkflow:
    """Deterministic MVP workflow that preserves the real run contract."""

    def __init__(
        self,
        run_store: RunStore,
        event_store: EventStore,
        artifact_store: ArtifactStore,
        retriever: Retriever | None = None,
        reranker: Reranker | None = None,
        diversity_policy: SourceDiversityPolicy | None = None,
        research_planner: ResearchPlanner | None = None,
        report_writer: ReportWriter | None = None,
        citation_verifier: CitationVerifier | None = None,
        engine: WorkflowEngine | None = None,
        *,
        retrieval_top_k: int = 3,
        retrieval_candidate_limit: int = 6,
        step_delay_sec: float = 0.05,
    ):
        self.run_store = run_store
        self.event_store = event_store
        self.artifact_store = artifact_store
        self.retriever = retriever or LocalKeywordRetriever()
        self.reranker = reranker or NoopReranker()
        self.diversity_policy = diversity_policy or SourceDiversityPolicy()
        self.retrieval_top_k = retrieval_top_k
        self.retrieval_candidate_limit = retrieval_candidate_limit
        self.research_planner = research_planner or StaticResearchPlanner()
        self.report_writer = report_writer or EvidenceReportWriter()
        self.citation_verifier = citation_verifier or RuleBasedCitationVerifier()
        self.engine = engine or SequentialWorkflowEngine(
            run_store=run_store,
            event_store=event_store,
            artifact_store=artifact_store,
            step_delay_sec=step_delay_sec,
        )

    @property
    def step_delay_sec(self) -> float:
        return getattr(self.engine, "step_delay_sec", 0.0)

    @step_delay_sec.setter
    def step_delay_sec(self, value: float) -> None:
        self.engine.step_delay_sec = value

    async def run(self, run_id: str) -> None:
        run = self.run_store.get(run_id)
        if run is None:
            return
        if run.status == "cancelled":
            return

        state = WorkflowState(run=run)
        trace: list[dict] = []
        try:
            trace = await self.engine.execute(state, self._build_nodes())

            state.run = self.run_store.update(
                state.run.run_id,
                status="completed",
                current_step="completed",
                completed_steps=7,
                finished=True,
            )
            self.event_store.append(
                state.run,
                "report.completed",
                {"run_id": state.run.run_id, "artifact_path": "outputs/report.md"},
            )
            self.artifact_store.write_text(
                state.run,
                "logs/runtime.log",
                "MVP node workflow completed.\n",
            )
            trace.append(
                {
                    "node": "completion",
                    "status": "completed",
                    "started_at": datetime.now(UTC).isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "duration_ms": 0,
                    "event_type": "report.completed",
                    "artifacts": ["logs/runtime.log"],
                }
            )
            self.engine.write_trace(state.run, trace)
        except WorkflowCancelled:
            return
        except Exception as exc:
            failed = self.run_store.update(
                state.run.run_id,
                status="failed",
                current_step="failed",
                error=str(exc),
                finished=True,
            )
            self.event_store.append(
                failed,
                "run.failed",
                {"run_id": state.run.run_id, "error": str(exc)},
            )
            trace.append(
                {
                    "node": "failure",
                    "status": "failed",
                    "started_at": datetime.now(UTC).isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "duration_ms": 0,
                    "event_type": "run.failed",
                    "error": str(exc),
                }
            )
            self.engine.write_trace(failed, trace)

    def _build_nodes(self) -> list[WorkflowNode]:
        return [
            PlanningNode(self.research_planner, self.artifact_store),
            RetrievalNode(
                self.retriever,
                self.artifact_store,
                reranker=self.reranker,
                diversity_policy=self.diversity_policy,
                top_k=self.retrieval_top_k,
                candidate_limit=self.retrieval_candidate_limit,
            ),
            ReadingNode(),
            EvidenceExtractionNode(),
            VerificationNode(self.citation_verifier),
            ReportWritingNode(self.artifact_store, self.report_writer),
            EvaluationNode(self.artifact_store),
        ]
