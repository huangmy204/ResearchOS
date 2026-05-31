from __future__ import annotations

from dataclasses import dataclass

from researchos.retrieval.base import RetrievedChunk


@dataclass(frozen=True)
class SourceDiversityPolicy:
    max_chunks_per_source: int = 0

    @property
    def enabled(self) -> bool:
        return self.max_chunks_per_source > 0

    def select(self, chunks: list[RetrievedChunk], *, limit: int) -> list[RetrievedChunk]:
        if not self.enabled:
            return chunks[:limit]

        selected: list[RetrievedChunk] = []
        source_counts: dict[int, int] = {}
        for chunk in chunks:
            count = source_counts.get(chunk.document_index, 0)
            if count >= self.max_chunks_per_source:
                continue

            selected.append(chunk)
            source_counts[chunk.document_index] = count + 1
            if len(selected) == limit:
                break

        return selected
