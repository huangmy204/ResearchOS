from __future__ import annotations

from researchos.retrieval.base import Retriever
from researchos.retrieval.bm25 import BM25Retriever
from researchos.retrieval.local_text import LocalKeywordRetriever


def build_retriever(strategy: str) -> Retriever:
    normalized = strategy.strip().lower()
    if normalized in {"keyword", "local_keyword", "local-keyword"}:
        return LocalKeywordRetriever()
    if normalized == "bm25":
        return BM25Retriever()
    raise ValueError(f"Unknown retrieval strategy: {strategy}")
