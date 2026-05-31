from __future__ import annotations

from datetime import UTC, datetime

from researchos.models.run import ResearchDocument, ResearchRun
from researchos.retrieval.query_rewrite import RuleBasedQueryRewriter


def test_rule_based_query_rewriter_adds_domain_and_document_terms():
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="searching",
        query="case law hallucination",
        documents=[
            ResearchDocument(
                title="Legal AI memo",
                text="Unsupported citations create legal research risk.",
            )
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    rewritten = RuleBasedQueryRewriter().rewrite(
        run,
        failed_query="case law hallucination",
    )

    assert "citation" in rewritten
    assert "unsupported" in rewritten
    assert "legal" in rewritten
