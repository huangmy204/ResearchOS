from __future__ import annotations

from dataclasses import dataclass

from researchos.models.run import ResearchDocument
from researchos.retrieval.base import RetrievedChunk, Retriever
from researchos.retrieval.query_plan import QueryVariant


@dataclass(frozen=True)
class QueryVariantResult:
    kind: str
    query: str
    result_count: int


@dataclass(frozen=True)
class MultiQueryRetrievalResult:
    candidates: list[RetrievedChunk]
    query_results: list[QueryVariantResult]


def retrieve_with_query_variants(
    retriever: Retriever,
    queries: list[QueryVariant],
    documents: list[ResearchDocument],
    *,
    per_query_limit: int,
    merged_limit: int,
) -> MultiQueryRetrievalResult:
    candidates_by_key: dict[tuple[int, str], RetrievedChunk] = {}
    query_results: list[QueryVariantResult] = []

    for variant in queries:
        results = retriever.retrieve(
            variant.query,
            documents,
            limit=per_query_limit,
        )
        query_results.append(
            QueryVariantResult(
                kind=variant.kind,
                query=variant.query,
                result_count=len(results),
            )
        )
        for chunk in results:
            key = (chunk.document_index, chunk.text)
            previous = candidates_by_key.get(key)
            if previous is None or chunk.score > previous.score:
                candidates_by_key[key] = chunk

    merged = sorted(
        candidates_by_key.values(),
        key=lambda chunk: (chunk.score, -chunk.document_index, chunk.title),
        reverse=True,
    )
    return MultiQueryRetrievalResult(
        candidates=merged[:merged_limit],
        query_results=query_results,
    )
