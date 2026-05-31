from __future__ import annotations

from typing import Protocol

from researchos.retrieval.base import RetrievedChunk
from researchos.retrieval.local_text import tokenize


class Reranker(Protocol):
    name: str
    score_type: str

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        """Reorder retrieved chunks and return the final top-k evidence candidates."""


class NoopReranker:
    name = "none"
    score_type = "none"

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        return chunks[:limit]


class TermOverlapReranker:
    name = "term_overlap"
    score_type = "query_chunk_overlap"

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return chunks[:limit]

        ranked = sorted(
            enumerate(chunks),
            key=lambda item: (
                _overlap_score(query_terms, item[1]),
                item[1].score,
                -item[0],
            ),
            reverse=True,
        )
        return [chunk for _, chunk in ranked[:limit]]


def build_reranker(name: str) -> Reranker:
    normalized = name.strip().lower()
    if normalized in {"", "none", "noop", "disabled"}:
        return NoopReranker()
    if normalized in {"term_overlap", "term-overlap", "overlap"}:
        return TermOverlapReranker()
    raise ValueError(f"Unknown reranker: {name}")


def _overlap_score(query_terms: set[str], chunk: RetrievedChunk) -> float:
    chunk_terms = set(tokenize(f"{chunk.title} {chunk.text}"))
    return len(query_terms & chunk_terms) / len(query_terms)
