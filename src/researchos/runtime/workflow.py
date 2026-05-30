from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter

from researchos.models.run import ResearchRun
from researchos.planning import ResearchPlanner, StaticResearchPlanner
from researchos.reporting import EvidenceReportWriter, ReportWriter
from researchos.retrieval import LocalKeywordRetriever, Retriever
from researchos.runtime.nodes import (
    EvaluationNode,
    EvidenceExtractionNode,
    PlanningNode,
    ReadingNode,
    ReportWritingNode,
    RetrievalNode,
    VerificationNode,
)
from researchos.runtime.state import NodeResult, WorkflowNode, WorkflowState
from researchos.stores.artifact_store import ArtifactStore
from researchos.stores.event_store import EventStore
from researchos.stores.run_store import RunStore
from researchos.verification import CitationVerifier, RuleBasedCitationVerifier


class WorkflowCancelled(Exception):
    """Raised internally when a run is cancelled while the workflow is active."""


class ResearchWorkflow:
    """Deterministic MVP workflow that preserves the real run contract."""

    def __init__(
        self,
        run_store: RunStore,
        event_store: EventStore,
        artifact_store: ArtifactStore,
        retriever: Retriever | None = None,
        research_planner: ResearchPlanner | None = None,
        report_writer: ReportWriter | None = None,
        citation_verifier: CitationVerifier | None = None,
        *,
        step_delay_sec: float = 0.05,
    ):
        self.run_store = run_store
        self.event_store = event_store
        self.artifact_store = artifact_store
        self.retriever = retriever or LocalKeywordRetriever()
        self.research_planner = research_planner or StaticResearchPlanner()
        self.report_writer = report_writer or EvidenceReportWriter()
        self.citation_verifier = citation_verifier or RuleBasedCitationVerifier()
        self.step_delay_sec = step_delay_sec

    async def run(self, run_id: str) -> None:
        run = self.run_store.get(run_id)
        if run is None:
            return
        if run.status == "cancelled":
            return

        state = WorkflowState(run=run)
        trace: list[dict] = []
        try:
            for node in self._build_nodes():
                await self._execute_node(state, node, trace)

            self._raise_if_cancelled(state.run.run_id)
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
            self._write_workflow_trace(state.run, trace)
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
            self._write_workflow_trace(failed, trace)

    async def _execute_node(
        self,
        state: WorkflowState,
        node: WorkflowNode,
        trace: list[dict],
    ) -> None:
        self._raise_if_cancelled(state.run.run_id)
        started_at = datetime.now(UTC)
        start = perf_counter()
        result = node.execute(state)
        duration_ms = round((perf_counter() - start) * 1000, 2)
        state.run = await self._advance(state.run, result=result)
        trace.append(self._trace_entry(result, started_at, duration_ms))
        self._write_workflow_trace(state.run, trace)
        await self._pause(state.run.run_id)

    def _build_nodes(self) -> list[WorkflowNode]:
        return [
            PlanningNode(self.research_planner, self.artifact_store),
            RetrievalNode(self.retriever),
            ReadingNode(),
            EvidenceExtractionNode(),
            VerificationNode(self.citation_verifier),
            ReportWritingNode(self.artifact_store, self.report_writer),
            EvaluationNode(self.artifact_store),
        ]

    async def _advance(
        self,
        run: ResearchRun,
        *,
        result: NodeResult,
    ) -> ResearchRun:
        current = self.run_store.get(run.run_id)
        if current and current.status == "cancelled":
            return current
        updated = self.run_store.update(
            run.run_id,
            status=result.status,
            current_step=result.step_name,
            completed_steps=result.completed_steps,
        )
        self.event_store.append(updated, result.event_type, result.payload)
        return updated

    async def _pause(self, run_id: str) -> None:
        if self.step_delay_sec > 0:
            await asyncio.sleep(self.step_delay_sec)
        self._raise_if_cancelled(run_id)

    def _raise_if_cancelled(self, run_id: str) -> None:
        current = self.run_store.get(run_id)
        if current and current.status == "cancelled":
            raise WorkflowCancelled

    def _trace_entry(
        self,
        result: NodeResult,
        started_at: datetime,
        duration_ms: float,
    ) -> dict:
        return {
            "node": result.node_name,
            "status": result.status,
            "step_name": result.step_name,
            "completed_steps": result.completed_steps,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "duration_ms": duration_ms,
            "event_type": result.event_type,
            "artifacts": result.artifacts,
        }

    def _write_workflow_trace(self, run: ResearchRun, trace: list[dict]) -> None:
        self.artifact_store.write_json(
            run,
            "traces/workflow_trace.json",
            {"run_id": run.run_id, "nodes": trace},
        )
