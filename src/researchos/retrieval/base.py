from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from researchos.models.run import ResearchDocument


@dataclass(frozen=True)
class RetrievedChunk:
    document_index: int
    title: str
    text: str
    score: float
    url: str | None = None


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        documents: list[ResearchDocument],
        *,
        limit: int = 3,
    ) -> list[RetrievedChunk]:
        """Return the most relevant chunks for a query."""
