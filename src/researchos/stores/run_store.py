from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from researchos.models.run import ResearchRun, ResearchRunCreate, RunStatus
from researchos.stores.workspace import Workspace


class RunStore:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self._runs: dict[str, ResearchRun] = {}

    def create(self, request: ResearchRunCreate) -> ResearchRun:
        existing = self.find_by_request_id(request)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        run = ResearchRun(
            run_id=f"run_{uuid4().hex[:12]}",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            session_id=request.session_id,
            request_id=request.request_id,
            status="created",
            query=request.query,
            documents=request.documents,
            created_at=now,
            updated_at=now,
        )
        self._runs[run.run_id] = run
        self.workspace.ensure_run_layout(run)
        self.save(run)
        return run

    def find_by_request_id(self, request: ResearchRunCreate) -> ResearchRun | None:
        if request.request_id is None:
            return None

        for run in self._runs.values():
            if self._matches_request_id(run, request):
                return run

        root = self.workspace.root
        if not root.exists():
            return None

        pattern = (
            f"tenants/{request.tenant_id}/users/{request.user_id}/"
            f"sessions/{request.session_id}/runs/*/inputs/task.json"
        )
        for path in root.glob(pattern):
            data = json.loads(path.read_text(encoding="utf-8"))
            run = ResearchRun.model_validate(data)
            self._runs[run.run_id] = run
            if self._matches_request_id(run, request):
                return run
        return None

    def get(self, run_id: str) -> ResearchRun | None:
        if run_id in self._runs:
            return self._runs[run_id]
        return self._load_from_disk(run_id)

    def update(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        current_step: str | None = None,
        completed_steps: int | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> ResearchRun:
        run = self.get(run_id)
        if run is None:
            raise KeyError(run_id)

        updates = {"updated_at": datetime.now(UTC)}
        if status is not None:
            updates["status"] = status
        if current_step is not None:
            updates["current_step"] = current_step
        if completed_steps is not None:
            progress = dict(run.progress)
            progress["completed_steps"] = completed_steps
            updates["progress"] = progress
        if error is not None:
            updates["error"] = error
        if finished:
            updates["finished_at"] = datetime.now(UTC)

        updated = run.model_copy(update=updates)
        self._runs[run_id] = updated
        self.save(updated)
        return updated

    def list_all(self) -> list[ResearchRun]:
        self._load_all_from_disk()
        return sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)

    def save(self, run: ResearchRun) -> None:
        run_dir = self.workspace.ensure_run_layout(run)
        (run_dir / "inputs" / "task.json").write_text(
            run.model_dump_json(indent=2), encoding="utf-8"
        )

    def _load_from_disk(self, run_id: str) -> ResearchRun | None:
        root = self.workspace.root
        if not root.exists():
            return None

        for path in root.glob(f"tenants/*/users/*/sessions/*/runs/{run_id}/inputs/task.json"):
            run = self._load_run_file(path)
            return run
        return None

    def _load_all_from_disk(self) -> None:
        root = self.workspace.root
        if not root.exists():
            return

        for path in root.glob("tenants/*/users/*/sessions/*/runs/*/inputs/task.json"):
            self._load_run_file(path)

    def _load_run_file(self, path: Path) -> ResearchRun:
        data = json.loads(path.read_text(encoding="utf-8"))
        run = ResearchRun.model_validate(data)
        self._runs[run.run_id] = run
        return run

    def _matches_request_id(self, run: ResearchRun, request: ResearchRunCreate) -> bool:
        return (
            run.request_id == request.request_id
            and run.tenant_id == request.tenant_id
            and run.user_id == request.user_id
            and run.session_id == request.session_id
        )
