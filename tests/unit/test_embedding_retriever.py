from __future__ import annotations

from researchos.models.run import ResearchDocument
from researchos.retrieval.embedding import DeterministicHashEmbeddingModel, EmbeddingRetriever
from researchos.retrieval.factory import build_retriever


def test_deterministic_hash_embedding_model_returns_stable_vectors():
    model = DeterministicHashEmbeddingModel(dimension=16)

    first = model.embed("legal citation risk")
    second = model.embed("legal citation risk")

    assert first == second
    assert len(first) == 16


def test_embedding_retriever_ranks_relevant_document_first():
    retriever = EmbeddingRetriever()
    documents = [
        ResearchDocument(
            title="Cooking note",
            text="Sourdough bread needs flour, water, salt, and fermentation.",
        ),
        ResearchDocument(
            title="Legal AI memo",
            text=(
                "Legal research systems need citation verification. "
                "Unsupported citation evidence creates legal risk."
            ),
        ),
    ]

    chunks = retriever.retrieve("legal citation risk", documents, limit=1)

    assert len(chunks) == 1
    assert chunks[0].title == "Legal AI memo"
    assert chunks[0].score > 0


def test_embedding_retriever_uses_configured_chunk_size():
    retriever = EmbeddingRetriever(max_chunk_chars=45, chunk_overlap_chars=9)
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


def test_build_retriever_selects_embedding_strategy():
    retriever = build_retriever("embedding", max_chunk_chars=320, chunk_overlap_chars=40)

    assert retriever.__class__.__name__ == "EmbeddingRetriever"
    assert retriever.max_chunk_chars == 320
    assert retriever.chunk_overlap_chars == 40
