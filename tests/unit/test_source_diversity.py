from __future__ import annotations

from researchos.retrieval.base import RetrievedChunk
from researchos.retrieval.diversity import SourceDiversityPolicy


def test_source_diversity_policy_is_noop_when_disabled():
    chunks = [
        _chunk(document_index=0, text="first"),
        _chunk(document_index=0, text="second"),
        _chunk(document_index=1, text="third"),
    ]

    selected = SourceDiversityPolicy(max_chunks_per_source=0).select(chunks, limit=2)

    assert [chunk.text for chunk in selected] == ["first", "second"]


def test_source_diversity_policy_limits_chunks_per_source():
    chunks = [
        _chunk(document_index=0, text="first"),
        _chunk(document_index=0, text="second"),
        _chunk(document_index=1, text="third"),
        _chunk(document_index=2, text="fourth"),
    ]

    selected = SourceDiversityPolicy(max_chunks_per_source=1).select(chunks, limit=3)

    assert [chunk.text for chunk in selected] == ["first", "third", "fourth"]
    assert len({chunk.document_index for chunk in selected}) == 3


def _chunk(document_index: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_index=document_index,
        title=f"Doc {document_index}",
        text=text,
        score=1.0,
    )
