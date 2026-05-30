from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResearchEvent(BaseModel):
    event_id: str
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class ResearchEventListResponse(BaseModel):
    events: list[ResearchEvent]
