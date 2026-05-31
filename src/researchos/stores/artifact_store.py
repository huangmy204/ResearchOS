from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from researchos.models.artifact import ArtifactMetadata
from researchos.models.run import ResearchRun
from researchos.stores.workspace import Workspace

ARTIFACT_TYPES = {
    "outputs/report.md": ("report", "text/markdown"),
    "outputs/report.json": ("report_json", "application/json"),
    "outputs/executive_summary.md": ("executive_summary", "text/markdown"),
    "plans/research_plan.json": ("research_plan", "application/json"),
    "evidence/sources.json": ("sources", "application/json"),
    "evidence/evidence.json": ("evidence", "application/json"),
    "evidence/claims.json": ("claims", "application/json"),
    "evidence/evidence_graph.json": ("evidence_graph", "application/json"),
    "evidence/citation_verification.json": ("citation_verification", "application/json"),
    "sources/retrieval_diagnostics.json": ("retrieval_diagnostics", "application/json"),
    "sources/parsed/retrieval_results.json": ("retrieval_results", "application/json"),
    "traces/events.jsonl": ("events", "application/x-ndjson"),
    "traces/workflow_trace.json": ("workflow_trace", "application/json"),
    "evals/eval_result.json": ("eval_result", "application/json"),
    "evals/eval_report.md": ("eval_report", "text/markdown"),
    "logs/runtime.log": ("runtime_log", "text/plain"),
}


class ArtifactStore:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def list(self, run: ResearchRun) -> list[ArtifactMetadata]:
        run_dir = self.workspace.run_dir(run)
        artifacts: list[ArtifactMetadata] = []
        if not run_dir.exists():
            return artifacts

        for path in sorted(file for file in run_dir.rglob("*") if file.is_file()):
            logical_path = path.relative_to(run_dir).as_posix()
            artifact_type, mime_type = ARTIFACT_TYPES.get(
                logical_path, ("file", self._guess_mime_type(path))
            )
            stat = path.stat()
            artifacts.append(
                ArtifactMetadata(
                    artifact_id=f"art_{run.run_id}_{logical_path.replace('/', '_')}",
                    run_id=run.run_id,
                    path=logical_path,
                    type=artifact_type,
                    mime_type=mime_type,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, UTC),
                )
            )
        return artifacts

    def read_text(self, run: ResearchRun, logical_path: str) -> tuple[str, str]:
        path = self.workspace.resolve_artifact_path(run, logical_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(logical_path)
        _, mime_type = ARTIFACT_TYPES.get(logical_path, ("file", self._guess_mime_type(path)))
        return path.read_text(encoding="utf-8"), mime_type

    def read_json(self, run: ResearchRun, logical_path: str) -> object:
        content, mime_type = self.read_text(run, logical_path)
        if mime_type != "application/json":
            raise ValueError(f"Artifact is not JSON: {logical_path}")
        return json.loads(content)

    def write_json(self, run: ResearchRun, logical_path: str, data: object) -> None:
        path = self.workspace.resolve_artifact_path(run, logical_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_text(self, run: ResearchRun, logical_path: str, text: str) -> None:
        path = self.workspace.resolve_artifact_path(run, logical_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _guess_mime_type(self, path: Path) -> str:
        if path.suffix == ".json":
            return "application/json"
        if path.suffix == ".jsonl":
            return "application/x-ndjson"
        if path.suffix == ".md":
            return "text/markdown"
        return "text/plain"
