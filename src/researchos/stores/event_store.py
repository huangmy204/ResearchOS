from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from researchos.models.event import ResearchEvent
from researchos.models.run import ResearchRun
from researchos.stores.workspace import Workspace


class EventStore:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self._events: dict[str, list[ResearchEvent]] = {}

    def append(
        self, run: ResearchRun, event_type: str, payload: dict, *, sequence: int | None = None
    ) -> ResearchEvent:
        events = self._events.setdefault(run.run_id, [])
        event = ResearchEvent(
            event_id=f"evt_{uuid4().hex[:12]}",
            run_id=run.run_id,
            sequence=sequence if sequence is not None else len(events) + 1,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        events.append(event)

        run_dir = self.workspace.ensure_run_layout(run)
        events_path = run_dir / "traces" / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as file:
            file.write(event.model_dump_json() + "\n")
        return event

    def list(self, run: ResearchRun, after_sequence: int = 0) -> list[ResearchEvent]:
        if run.run_id not in self._events:
            self._events[run.run_id] = self._load(run)
        return [event for event in self._events[run.run_id] if event.sequence > after_sequence]

    def _load(self, run: ResearchRun) -> list[ResearchEvent]:
        events_path = self.workspace.run_dir(run) / "traces" / "events.jsonl"
        if not events_path.exists():
            return []
        events = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(ResearchEvent.model_validate(json.loads(line)))
        return events
