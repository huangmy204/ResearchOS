from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.trace import WorkflowTraceNode, WorkflowTraceResponse

router = APIRouter(prefix="/v1/research-runs", tags=["trace"])


@router.get("/{run_id}/trace", response_model=WorkflowTraceResponse)
def get_workflow_trace(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> WorkflowTraceResponse:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")

    try:
        trace = services.artifact_store.read_json(run, "traces/workflow_trace.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow trace not found.") from exc

    nodes = [WorkflowTraceNode.model_validate(item) for item in trace.get("nodes", [])]
    return WorkflowTraceResponse(
        run_id=run.run_id,
        nodes=nodes,
        summary={
            "node_count": len(nodes),
            "total_duration_ms": round(sum(node.duration_ms for node in nodes), 2),
            "completed": bool(nodes and nodes[-1].status == "completed"),
            "node_names": [node.node for node in nodes],
        },
    )
