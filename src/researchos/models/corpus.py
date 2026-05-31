from __future__ import annotations

from pydantic import BaseModel, Field


class CorpusFile(BaseModel):
    path: str
    title: str
    size_bytes: int
    suffix: str


class CorpusListResponse(BaseModel):
    corpus_root: str
    files: list[CorpusFile]


class CorpusDocumentCreate(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    path: str | None = None
    overwrite: bool = False


class CorpusDocumentResponse(BaseModel):
    path: str
    title: str
    text: str
    size_bytes: int
    suffix: str
