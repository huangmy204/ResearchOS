from __future__ import annotations

import hashlib
import math
from typing import Protocol

from researchos.models.run import ResearchDocument
from researchos.retrieval.base import RetrievedChunk
from researchos.retrieval.local_text import chunk_text, tokenize


class EmbeddingModel(Protocol):
    def embed(self, text: str) -> list[float]:
        """Convert text into a numeric vector."""


class DeterministicHashEmbeddingModel:
    def __init__(self, *, dimension: int = 64):
        if dimension <= 0:
            raise ValueError("dimension must be greater than 0.")
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return _normalize(vector)


class EmbeddingRetriever:
    strategy_name = "embedding"
    score_type = "cosine_similarity"

    def __init__(
        self,
        *,
        max_chunk_chars: int = 600,
        chunk_overlap_chars: int = 0,
        embedding_model: EmbeddingModel | None = None,
    ):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.embedding_model = embedding_model or DeterministicHashEmbeddingModel()

    def retrieve(
        self,
        query: str,
        documents: list[ResearchDocument],
        *,
        limit: int = 3,
    ) -> list[RetrievedChunk]:
        if not tokenize(query):
            return []

        query_vector = self.embedding_model.embed(query)
        chunks: list[RetrievedChunk] = []
        for document_index, document in enumerate(documents):
            for chunk in chunk_text(
                document.text,
                max_chars=self.max_chunk_chars,
                overlap_chars=self.chunk_overlap_chars,
            ):
                chunk_vector = self.embedding_model.embed(f"{document.title}\n{chunk}")
                score = _cosine_similarity(query_vector, chunk_vector)
                chunks.append(
                    RetrievedChunk(
                        document_index=document_index,
                        title=document.title,
                        text=chunk,
                        score=round(score, 4),
                        url=document.url,
                    )
                )

        ranked = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)
        positive = [chunk for chunk in ranked if chunk.score > 0]
        return positive[:limit]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
