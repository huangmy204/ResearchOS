from __future__ import annotations

from researchos.models.run import ResearchDocument
from researchos.retrieval.bm25 import BM25Retriever
from researchos.retrieval.factory import build_retriever


def test_bm25_retriever_ranks_repeated_relevant_terms_higher():
    retriever = BM25Retriever()
    documents = [
        ResearchDocument(
            title="General AI note",
            text="AI systems can support many knowledge work tasks.",
        ),
        ResearchDocument(
            title="Citation risk memo",
            text=(
                "Legal citation risk requires citation verification. "
                "Unsupported citation references create legal research risk."
            ),
        ),
    ]

    chunks = retriever.retrieve("legal citation risk", documents, limit=1)

    assert len(chunks) == 1
    assert chunks[0].title == "Citation risk memo"
    assert chunks[0].score > 0


def test_bm25_retriever_returns_no_chunks_without_overlap():
    retriever = BM25Retriever()
    documents = [
        ResearchDocument(title="Cooking note", text="Flour water salt fermentation."),
    ]

    chunks = retriever.retrieve("legal citation risk", documents)

    assert chunks == []


def test_build_retriever_selects_supported_strategies():
    assert build_retriever("keyword").__class__.__name__ == "LocalKeywordRetriever"
    assert build_retriever("bm25").__class__.__name__ == "BM25Retriever"
