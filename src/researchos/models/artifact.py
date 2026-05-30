from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ArtifactMetadata(BaseModel):
    artifact_id: str
    run_id: str
    path: str
    type: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactMetadata]
