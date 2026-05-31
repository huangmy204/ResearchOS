from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowTraceNode(BaseModel):
    node: str
    status: str
    step_name: str | None = None
    completed_steps: int | None = None
    started_at: str
    finished_at: str
    duration_ms: float
    event_type: str
    artifacts: list[str] = Field(default_factory=list)
    error: str | None = None


class WorkflowTraceResponse(BaseModel):
    run_id: str
    nodes: list[WorkflowTraceNode]
    summary: dict[str, Any]
