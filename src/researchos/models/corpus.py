from __future__ import annotations

from pydantic import BaseModel


class CorpusFile(BaseModel):
    path: str
    title: str
    size_bytes: int
    suffix: str


class CorpusListResponse(BaseModel):
    corpus_root: str
    files: list[CorpusFile]
