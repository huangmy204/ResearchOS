from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from researchos.models.run import ResearchDocument

SUPPORTED_CORPUS_SUFFIXES = {".md", ".txt"}


@dataclass(frozen=True)
class CorpusFileRecord:
    path: str
    title: str
    size_bytes: int


@dataclass(frozen=True)
class LoadedCorpus:
    documents: list[ResearchDocument]
    files: list[CorpusFileRecord]


class LocalCorpusLoader:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root

    def load(self, *, relative_paths: list[str] | None = None) -> LoadedCorpus:
        paths = (
            [self._resolve_relative_path(path) for path in relative_paths]
            if relative_paths
            else self._discover_files()
        )
        documents: list[ResearchDocument] = []
        files: list[CorpusFileRecord] = []
        for path in paths:
            if not path.exists() or not path.is_file():
                raise FileNotFoundError(path)
            if path.suffix.lower() not in SUPPORTED_CORPUS_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            title = _extract_title(path, text)
            relative = path.relative_to(self.corpus_root).as_posix()
            documents.append(
                ResearchDocument(
                    title=title,
                    text=text,
                    url=f"corpus://{relative}",
                )
            )
            files.append(
                CorpusFileRecord(
                    path=relative,
                    title=title,
                    size_bytes=path.stat().st_size,
                )
            )
        return LoadedCorpus(documents=documents, files=files)

    def _discover_files(self) -> list[Path]:
        if not self.corpus_root.exists():
            return []
        return sorted(
            path
            for path in self.corpus_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_CORPUS_SUFFIXES
        )

    def _resolve_relative_path(self, relative_path: str) -> Path:
        if not relative_path or relative_path.startswith(("/", "\\")):
            raise ValueError("Corpus path must be relative.")
        root = self.corpus_root.resolve()
        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("Corpus path escapes the corpus root.")
        return candidate


def _extract_title(path: Path, text: str) -> str:
    if path.suffix.lower() == ".md":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    return title
    return path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled document"
