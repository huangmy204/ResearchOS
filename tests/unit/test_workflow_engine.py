from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from researchos.models.run import ResearchRun
from researchos.runtime.engine import SequentialWorkflowEngine
from researchos.runtime.state import NodeResult, WorkflowState
from researchos.stores import ArtifactStore, EventStore, RunStore, Workspace


class StaticNode:
    name = "static_node"

    def execute(self, state: WorkflowState) -> NodeResult:
        state.plan = [{"step_id": "step_001", "agent": "planner"}]
        return NodeResult(
            node_name=self.name,
            status="planning",
            step_name="static planning",
            completed_steps=1,
            event_type="plan.created",
            payload={"run_id": state.run.run_id, "steps": state.plan},
            artifacts=["plans/research_plan.json"],
        )


def test_sequential_workflow_engine_executes_nodes_and_writes_trace(tmp_path):
    workspace = Workspace(tmp_path / "workspace")
    workspace.initialize()
    run_store = RunStore(workspace)
    event_store = EventStore(workspace)
    artifact_store = ArtifactStore(workspace)
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="created",
        query="test query",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    run_store.save(run)
    engine = SequentialWorkflowEngine(
        run_store=run_store,
        event_store=event_store,
        artifact_store=artifact_store,
        step_delay_sec=0,
    )
    state = WorkflowState(run=run)

    trace = asyncio.run(engine.execute(state, [StaticNode()]))

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "planning"
    assert updated.current_step == "static planning"
    assert state.plan[0]["agent"] == "planner"
    assert trace[0]["node"] == "static_node"
    assert trace[0]["event_type"] == "plan.created"
    persisted_trace = artifact_store.read_json(updated, "traces/workflow_trace.json")
    assert persisted_trace["nodes"][0]["node"] == "static_node"
