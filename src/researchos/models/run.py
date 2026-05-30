from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RunStatus = Literal[
    "created",
    "planning",
    "searching",
    "reading",
    "extracting_evidence",
    "verifying",
    "writing",
    "reviewing",
    "completed",
    "failed",
    "cancelled",
]


class ResearchDocument(BaseModel):
    title: str = "Untitled document"
    text: str = Field(min_length=1)
    url: str | None = None


class ResearchRunCreate(BaseModel):
    tenant_id: str = "default"
    user_id: str = "default"
    session_id: str = "default"
    request_id: str | None = None
    query: str = Field(min_length=1)
    documents: list[ResearchDocument] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)


class ResearchRun(BaseModel):
    run_id: str
    tenant_id: str = "default"
    user_id: str = "default"
    session_id: str
    request_id: str | None = None
    status: RunStatus
    query: str
    documents: list[ResearchDocument] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    error: str | None = None
    current_step: str | None = None
    progress: dict[str, int] = Field(
        default_factory=lambda: {"completed_steps": 0, "total_steps": 7}
    )


class ResearchRunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus
    events_url: str
    artifacts_url: str


class ResearchRunListResponse(BaseModel):
    runs: list[ResearchRun]
