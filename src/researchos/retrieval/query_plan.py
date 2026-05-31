from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from researchos.models.run import ResearchRun
from researchos.retrieval.local_text import tokenize


@dataclass(frozen=True)
class QueryVariant:
    kind: str
    query: str


class QueryPlanner(Protocol):
    name: str

    def plan(self, run: ResearchRun, *, active_query: str) -> list[QueryVariant]:
        """Build retrieval query variants for a single retrieval attempt."""


class RuleBasedMultiQueryPlanner:
    name = "rule_based_multi_query"

    def plan(self, run: ResearchRun, *, active_query: str) -> list[QueryVariant]:
        variants = [
            QueryVariant(kind="active", query=active_query),
            QueryVariant(kind="original", query=run.query),
        ]
        variants.extend(_subquestion_variants(active_query))
        variants.append(QueryVariant(kind="upshift", query=_upshift_query(active_query)))
        return _dedupe_variants(variants)


def _subquestion_variants(query: str) -> list[QueryVariant]:
    terms = tokenize(query)
    if not terms:
        return []

    if len(terms) == 1:
        return [QueryVariant(kind="subquestion", query=query)]

    midpoint = max(1, len(terms) // 2)
    return [
        QueryVariant(kind="subquestion", query=" ".join(terms[:midpoint])),
        QueryVariant(kind="subquestion", query=" ".join(terms[midpoint:])),
    ]


def _upshift_query(query: str) -> str:
    terms = tokenize(query)
    if not terms:
        return query
    return " ".join(["overview", "background", "context", *terms])


def _dedupe_variants(variants: list[QueryVariant]) -> list[QueryVariant]:
    deduped: list[QueryVariant] = []
    seen: set[str] = set()
    for variant in variants:
        normalized = " ".join(tokenize(variant.query))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(QueryVariant(kind=variant.kind, query=variant.query))
    return deduped
