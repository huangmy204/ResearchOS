from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Protocol

from langgraph.graph import END, START, StateGraph

from researchos.models.run import ResearchRun
from researchos.runtime.state import NodeResult, WorkflowNode, WorkflowState
from researchos.stores.artifact_store import ArtifactStore
from researchos.stores.event_store import EventStore
from researchos.stores.run_store import RunStore


class WorkflowCancelled(Exception):
    """Raised internally when a run is cancelled while the workflow is active."""


class WorkflowEngine(Protocol):
    async def execute(
        self,
        state: WorkflowState,
        nodes: list[WorkflowNode],
    ) -> list[dict]:
        """Execute workflow nodes and return trace entries."""

    def write_trace(self, run: ResearchRun, trace: list[dict]) -> None:
        """Persist workflow trace metadata."""


class SequentialWorkflowEngine:
    def __init__(
        self,
        *,
        run_store: RunStore,
        event_store: EventStore,
        artifact_store: ArtifactStore,
        step_delay_sec: float = 0.05,
    ):
        self.run_store = run_store
        self.event_store = event_store
        self.artifact_store = artifact_store
        self.step_delay_sec = step_delay_sec

    async def execute(
        self,
        state: WorkflowState,
        nodes: list[WorkflowNode],
    ) -> list[dict]:
        trace: list[dict] = []
        for node in nodes:
            await self._execute_node(state, node, trace)
        return trace

    def write_trace(self, run: ResearchRun, trace: list[dict]) -> None:
        self.artifact_store.write_json(
            run,
            "traces/workflow_trace.json",
            {"run_id": run.run_id, "nodes": trace},
        )

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
        state.run = self._advance(state.run, result=result)
        trace.append(_trace_entry(result, started_at, duration_ms))
        self.write_trace(state.run, trace)
        await self._pause(state.run.run_id)

    def _advance(
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


class LangGraphWorkflowEngine(SequentialWorkflowEngine):
    async def execute(
        self,
        state: WorkflowState,
        nodes: list[WorkflowNode],
    ) -> list[dict]:
        if not nodes:
            return []

        graph = StateGraph(dict)
        for node in nodes:
            graph.add_node(node.name, self._build_graph_node(node))

        graph.add_edge(START, nodes[0].name)
        for previous, current in zip(nodes, nodes[1:], strict=False):
            graph.add_edge(previous.name, current.name)
        graph.add_edge(nodes[-1].name, END)

        app = graph.compile()
        result = await app.ainvoke({"workflow_state": state, "trace": []})
        return result["trace"]

    def _build_graph_node(self, node: WorkflowNode):
        async def run_node(graph_state: dict[str, Any]) -> dict[str, Any]:
            workflow_state = graph_state["workflow_state"]
            trace = graph_state["trace"]
            await self._execute_node(workflow_state, node, trace)
            return graph_state

        return run_node


def _trace_entry(
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
