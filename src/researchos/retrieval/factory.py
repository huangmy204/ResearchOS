from __future__ import annotations

from researchos.retrieval.base import Retriever
from researchos.retrieval.bm25 import BM25Retriever
from researchos.retrieval.embedding import EmbeddingRetriever
from researchos.retrieval.local_text import LocalKeywordRetriever


def build_retriever(
    strategy: str,
    *,
    max_chunk_chars: int = 600,
    chunk_overlap_chars: int = 0,
) -> Retriever:
    normalized = strategy.strip().lower()
    if normalized in {"keyword", "local_keyword", "local-keyword"}:
        return LocalKeywordRetriever(
            max_chunk_chars=max_chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars,
        )
    if normalized == "bm25":
        return BM25Retriever(
            max_chunk_chars=max_chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars,
        )
    if normalized in {"embedding", "embeddings", "vector", "deterministic_embedding"}:
        return EmbeddingRetriever(
            max_chunk_chars=max_chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars,
        )
    raise ValueError(f"Unknown retrieval strategy: {strategy}")
