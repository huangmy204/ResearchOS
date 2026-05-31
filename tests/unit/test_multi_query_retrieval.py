from __future__ import annotations

from researchos.models.run import ResearchDocument
from researchos.retrieval.local_text import LocalKeywordRetriever
from researchos.retrieval.multi_query import retrieve_with_query_variants
from researchos.retrieval.query_plan import QueryVariant


def test_multi_query_retrieval_merges_and_dedupes_candidates():
    documents = [
        ResearchDocument(
            title="Legal memo",
            text="Legal citation risk requires careful verification.",
        )
    ]
    retriever = LocalKeywordRetriever()

    result = retrieve_with_query_variants(
        retriever,
        [
            QueryVariant(kind="original", query="legal citation risk"),
            QueryVariant(kind="subquestion", query="citation risk"),
        ],
        documents,
        per_query_limit=3,
        merged_limit=3,
    )

    assert len(result.query_results) == 2
    assert result.query_results[0].result_count == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].title == "Legal memo"
