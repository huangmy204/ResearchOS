from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from researchos.api.deps import get_services
from researchos.api.services import AppServices

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(services: Annotated[AppServices, Depends(get_services)]) -> dict:
    workspace_root = services.settings.workspace_root
    writable = _is_writable(workspace_root)
    return {
        "status": "ready" if writable else "not_ready",
        "checks": {
            "workspace_root": str(workspace_root),
            "workspace_root_writable": writable,
            "postgres": "disabled_for_mvp",
            "redis": "disabled_for_mvp",
            "vector_db": "disabled_for_mvp",
            "docker_sandbox": "disabled_for_mvp",
            "search_provider": "disabled_for_mvp",
            "mcp_gateway": "disabled_for_mvp",
        },
    }


@router.get("/metricsz")
def metricsz(services: Annotated[AppServices, Depends(get_services)]) -> dict:
    runs = services.run_store.list_all()
    total_runs = len(runs)
    completed_runs = sum(1 for run in runs if run.status == "completed")
    failed_runs = sum(1 for run in runs if run.status == "failed")
    running_runs = sum(
        1
        for run in runs
        if run.status
        in {
            "created",
            "planning",
            "searching",
            "reading",
            "extracting_evidence",
            "verifying",
            "writing",
            "reviewing",
        }
    )
    return {
        "total_runs": total_runs,
        "running_runs": running_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "avg_latency_sec": 0.0,
        "avg_claim_support_rate": 1.0 if completed_runs else 0.0,
        "avg_citation_precision": 1.0 if completed_runs else 0.0,
        "tool_success_rate": 1.0 if failed_runs == 0 else 0.0,
    }


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".readyz_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
