from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from researchos.ingestion.local_corpus import LocalCorpusLoader


@dataclass(frozen=True)
class CorpusIndexEntry:
    path: str
    title: str
    size_bytes: int
    suffix: str
    modified_at: str
    content_sha256: str
    status: str = "ready"


@dataclass(frozen=True)
class CorpusIndexManifest:
    version: int
    corpus_root: str
    indexed_at: str | None
    document_count: int
    entries: list[CorpusIndexEntry]


class LocalCorpusIndex:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root
        self.loader = LocalCorpusLoader(corpus_root)
        self.manifest_path = corpus_root / ".researchos" / "index_manifest.json"

    def build(self) -> CorpusIndexManifest:
        entries = [_build_entry(self.loader, file.path) for file in self.loader.list_files()]
        manifest = CorpusIndexManifest(
            version=1,
            corpus_root=str(self.corpus_root),
            indexed_at=datetime.now(UTC).isoformat(),
            document_count=len(entries),
            entries=entries,
        )
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(_manifest_to_dict(manifest), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

    def read(self) -> CorpusIndexManifest:
        if not self.manifest_path.exists():
            return CorpusIndexManifest(
                version=1,
                corpus_root=str(self.corpus_root),
                indexed_at=None,
                document_count=0,
                entries=[],
            )
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return _manifest_from_dict(data)


def _build_entry(loader: LocalCorpusLoader, relative_path: str) -> CorpusIndexEntry:
    document = loader.read_document(relative_path)
    path = loader._resolve_relative_path(relative_path)
    stat = path.stat()
    return CorpusIndexEntry(
        path=document.path,
        title=document.title,
        size_bytes=document.size_bytes,
        suffix=document.suffix,
        modified_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        content_sha256=hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
    )


def _manifest_to_dict(manifest: CorpusIndexManifest) -> dict:
    return {
        "version": manifest.version,
        "corpus_root": manifest.corpus_root,
        "indexed_at": manifest.indexed_at,
        "document_count": manifest.document_count,
        "entries": [asdict(entry) for entry in manifest.entries],
    }


def _manifest_from_dict(data: dict) -> CorpusIndexManifest:
    entries = [CorpusIndexEntry(**entry) for entry in data.get("entries", [])]
    return CorpusIndexManifest(
        version=int(data.get("version", 1)),
        corpus_root=str(data.get("corpus_root", "")),
        indexed_at=data.get("indexed_at"),
        document_count=int(data.get("document_count", len(entries))),
        entries=entries,
    )
