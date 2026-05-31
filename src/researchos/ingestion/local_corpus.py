from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from researchos.models.run import ResearchDocument

SUPPORTED_CORPUS_SUFFIXES = {".md", ".txt"}


@dataclass(frozen=True)
class CorpusFileRecord:
    path: str
    title: str
    size_bytes: int
    suffix: str = ""


@dataclass(frozen=True)
class LoadedCorpus:
    documents: list[ResearchDocument]
    files: list[CorpusFileRecord]


@dataclass(frozen=True)
class CorpusDocumentRecord:
    path: str
    title: str
    text: str
    size_bytes: int
    suffix: str


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
            relative = self._relative_path(path)
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
                    suffix=path.suffix.lower(),
                )
            )
        return LoadedCorpus(documents=documents, files=files)

    def list_files(self) -> list[CorpusFileRecord]:
        files: list[CorpusFileRecord] = []
        for path in self._discover_files():
            text = path.read_text(encoding="utf-8").strip()
            title = _extract_title(path, text) if text else _extract_title(path, "")
            files.append(
                CorpusFileRecord(
                    path=self._relative_path(path),
                    title=title,
                    size_bytes=path.stat().st_size,
                    suffix=path.suffix.lower(),
                )
            )
        return files

    def read_document(self, relative_path: str) -> CorpusDocumentRecord:
        path = self._resolve_relative_path(relative_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() not in SUPPORTED_CORPUS_SUFFIXES:
            raise ValueError(f"Unsupported corpus file type: {path.suffix}")
        text = path.read_text(encoding="utf-8")
        return CorpusDocumentRecord(
            path=self._relative_path(path),
            title=_extract_title(path, text),
            text=text,
            size_bytes=path.stat().st_size,
            suffix=path.suffix.lower(),
        )

    def write_document(
        self,
        *,
        title: str,
        text: str,
        relative_path: str | None = None,
        overwrite: bool = False,
    ) -> CorpusDocumentRecord:
        if not title.strip():
            raise ValueError("Corpus document title is required.")
        if not text.strip():
            raise ValueError("Corpus document text is required.")

        path = (
            self._resolve_relative_path(relative_path)
            if relative_path
            else self._resolve_relative_path(f"{_slugify(title)}.md")
        )
        if path.suffix.lower() not in SUPPORTED_CORPUS_SUFFIXES:
            raise ValueError(f"Unsupported corpus file type: {path.suffix}")
        if path.exists() and not overwrite:
            raise FileExistsError(path)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_format_corpus_text(path, title, text), encoding="utf-8")
        return self.read_document(self._relative_path(path))

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

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.corpus_root.resolve()).as_posix()


def _extract_title(path: Path, text: str) -> str:
    if path.suffix.lower() == ".md":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    return title
    return path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled document"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "untitled-document"


def _format_corpus_text(path: Path, title: str, text: str) -> str:
    normalized = text.strip()
    if path.suffix.lower() == ".md" and not normalized.lstrip().startswith("#"):
        return f"# {title.strip()}\n\n{normalized}\n"
    return f"{normalized}\n"
