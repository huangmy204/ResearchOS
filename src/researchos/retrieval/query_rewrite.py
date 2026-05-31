from __future__ import annotations

from typing import Protocol

from researchos.models.run import ResearchRun
from researchos.retrieval.local_text import tokenize


class QueryRewriter(Protocol):
    name: str

    def rewrite(self, run: ResearchRun, *, failed_query: str) -> str:
        """Rewrite a failed retrieval query for a fallback retrieval attempt."""


class RuleBasedQueryRewriter:
    name = "rule_based"

    def rewrite(self, run: ResearchRun, *, failed_query: str) -> str:
        original_terms = tokenize(failed_query)
        expansion_terms = _domain_expansion_terms(original_terms)
        document_terms = _document_title_terms(run)
        combined = [*original_terms, *expansion_terms, *document_terms]
        deduped = list(dict.fromkeys(combined))
        return " ".join(deduped) if deduped else failed_query


def _domain_expansion_terms(query_terms: list[str]) -> list[str]:
    expansions: dict[str, list[str]] = {
        "hallucination": ["citation", "unsupported", "evidence", "verification"],
        "hallucinated": ["citation", "unsupported", "evidence", "verification"],
        "case": ["legal", "research", "citation"],
        "law": ["legal", "research", "citation"],
        "source": ["evidence", "citation", "verification"],
        "sources": ["evidence", "citation", "verification"],
    }
    terms: list[str] = []
    for term in query_terms:
        terms.extend(expansions.get(term, []))
    return terms


def _document_title_terms(run: ResearchRun) -> list[str]:
    terms: list[str] = []
    for document in run.documents:
        terms.extend(tokenize(document.title))
    return terms[:12]
