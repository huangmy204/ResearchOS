from __future__ import annotations

from datetime import UTC, datetime

import pytest

from researchos.models.run import ResearchRun
from researchos.stores.workspace import Workspace


def test_resolve_artifact_path_rejects_path_traversal(tmp_path):
    workspace = Workspace(tmp_path)
    run = ResearchRun(
        run_id="run_test",
        tenant_id="tenant",
        user_id="user",
        session_id="session",
        status="created",
        query="test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    workspace.ensure_run_layout(run)

    with pytest.raises(ValueError):
        workspace.resolve_artifact_path(run, "../outside.txt")


def test_ensure_run_layout_creates_expected_directories(tmp_path):
    workspace = Workspace(tmp_path)
    run = ResearchRun(
        run_id="run_test",
        tenant_id="tenant",
        user_id="user",
        session_id="session",
        status="created",
        query="test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    run_dir = workspace.ensure_run_layout(run)

    assert (run_dir / "inputs" / "uploaded_files").is_dir()
    assert (run_dir / "evidence").is_dir()
    assert (run_dir / "outputs").is_dir()
    assert (run_dir / "traces").is_dir()
