from __future__ import annotations

from researchos.retrieval.base import RetrievedChunk
from researchos.retrieval.rerank import NoopReranker, TermOverlapReranker, build_reranker


def test_noop_reranker_preserves_candidate_order():
    chunks = [
        _chunk("General note", "General unrelated text.", 0.9),
        _chunk("Legal memo", "Legal citation risk evidence.", 0.2),
    ]

    reranked = NoopReranker().rerank("legal citation risk", chunks, limit=2)

    assert [chunk.title for chunk in reranked] == ["General note", "Legal memo"]


def test_term_overlap_reranker_promotes_query_overlap():
    chunks = [
        _chunk("General note", "General unrelated text.", 0.9),
        _chunk("Legal memo", "Legal citation risk evidence.", 0.2),
    ]

    reranked = TermOverlapReranker().rerank("legal citation risk", chunks, limit=2)

    assert [chunk.title for chunk in reranked] == ["Legal memo", "General note"]


def test_build_reranker_selects_supported_rerankers():
    assert build_reranker("none").__class__.__name__ == "NoopReranker"
    assert build_reranker("term_overlap").__class__.__name__ == "TermOverlapReranker"


def _chunk(title: str, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_index=0,
        title=title,
        text=text,
        score=score,
    )
