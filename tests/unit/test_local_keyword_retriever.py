from __future__ import annotations

from researchos.models.run import ResearchDocument
from researchos.retrieval.local_text import LocalKeywordRetriever, chunk_text, tokenize


def test_local_keyword_retriever_ranks_relevant_document_first():
    retriever = LocalKeywordRetriever()
    documents = [
        ResearchDocument(
            title="Cooking note",
            text="Sourdough bread needs flour, water, salt, and fermentation.",
        ),
        ResearchDocument(
            title="Legal AI memo",
            text=(
                "AI agents can reduce legal research time. "
                "Citation hallucination is a key legal research risk."
            ),
        ),
    ]

    chunks = retriever.retrieve("legal research citation risk", documents, limit=1)

    assert len(chunks) == 1
    assert chunks[0].title == "Legal AI memo"
    assert chunks[0].score > 0


def test_local_keyword_retriever_returns_no_chunks_without_overlap():
    retriever = LocalKeywordRetriever()
    documents = [
        ResearchDocument(title="Cooking note", text="Flour water salt fermentation."),
    ]

    chunks = retriever.retrieve("legal citation risk", documents)

    assert chunks == []


def test_chunk_text_splits_long_paragraph_by_sentence_boundary():
    text = "Alpha sentence about research. Beta sentence about citations. Gamma sentence."

    chunks = chunk_text(text, max_chars=40)

    assert len(chunks) > 1
    assert all(len(chunk) <= 40 for chunk in chunks)
    assert chunks[0] == "Alpha sentence about research."


def test_chunk_text_can_add_overlap_between_adjacent_chunks():
    text = (
        "Alpha sentence about research. "
        "Beta sentence about citation risk. "
        "Gamma sentence."
    )

    chunks = chunk_text(text, max_chars=45, overlap_chars=9)

    assert chunks[1].startswith("research. Beta sentence")
    assert all(len(chunk) <= 45 for chunk in chunks)


def test_local_keyword_retriever_uses_configured_chunk_size():
    retriever = LocalKeywordRetriever(max_chunk_chars=45, chunk_overlap_chars=9)
    documents = [
        ResearchDocument(
            title="Legal AI memo",
            text=(
                "Alpha sentence about research. "
                "Beta sentence about citation risk. "
                "Gamma sentence about legal research."
            ),
        )
    ]

    chunks = retriever.retrieve("legal research citation risk", documents, limit=3)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 45 for chunk in chunks)


def test_tokenize_normalizes_case_and_punctuation():
    assert tokenize("Legal Research, CITATION risk!") == [
        "legal",
        "research",
        "citation",
        "risk",
    ]
