from __future__ import annotations

from datetime import UTC, datetime

from researchos.models.run import ResearchRun
from researchos.retrieval.query_plan import RuleBasedMultiQueryPlanner


def test_rule_based_multi_query_planner_builds_complementary_variants():
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="searching",
        query="impact of legal citation hallucination",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    variants = RuleBasedMultiQueryPlanner().plan(
        run,
        active_query="impact of legal citation hallucination",
    )

    kinds = [variant.kind for variant in variants]
    queries = [variant.query for variant in variants]

    assert kinds[0] == "active"
    assert "subquestion" in kinds
    assert "upshift" in kinds
    assert len(queries) == len(set(queries))
    assert any(query.startswith("overview background context") for query in queries)


def test_rule_based_multi_query_planner_includes_rewritten_active_query():
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="searching",
        query="case law hallucination",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    variants = RuleBasedMultiQueryPlanner().plan(
        run,
        active_query="case law hallucination citation unsupported evidence verification",
    )

    assert variants[0].kind == "active"
    assert "unsupported" in variants[0].query
    assert any(variant.kind == "original" for variant in variants)
