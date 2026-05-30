from __future__ import annotations

from pathlib import Path

from researchos.models.run import ResearchRun


class Workspace:
    def __init__(self, root: Path):
        self.root = root

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run: ResearchRun) -> Path:
        return (
            self.root
            / "tenants"
            / run.tenant_id
            / "users"
            / run.user_id
            / "sessions"
            / run.session_id
            / "runs"
            / run.run_id
        )

    def ensure_run_layout(self, run: ResearchRun) -> Path:
        run_dir = self.run_dir(run)
        for relative in [
            "inputs/uploaded_files",
            "sources/web_pages",
            "sources/pdfs",
            "sources/snapshots",
            "sources/parsed",
            "evidence",
            "outputs",
            "traces",
            "evals",
            "logs",
        ]:
            (run_dir / relative).mkdir(parents=True, exist_ok=True)
        return run_dir

    def resolve_artifact_path(self, run: ResearchRun, logical_path: str) -> Path:
        if not logical_path or logical_path.startswith(("/", "\\")):
            raise ValueError("Artifact path must be relative.")

        run_dir = self.run_dir(run).resolve()
        candidate = (run_dir / logical_path).resolve()

        if candidate != run_dir and run_dir not in candidate.parents:
            raise ValueError("Artifact path escapes the run workspace.")
        return candidate
