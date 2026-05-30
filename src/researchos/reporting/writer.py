from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun


@dataclass(frozen=True)
class ReportDraft:
    markdown: str
    report_json: dict
    executive_summary: str


class ReportWriter(Protocol):
    def write(
        self,
        *,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
    ) -> ReportDraft:
        """Build report artifacts from verified evidence."""


class EvidenceReportWriter:
    def write(
        self,
        *,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
    ) -> ReportDraft:
        retrieval_backed = source.source_type == "file"
        summary = (
            "This run used local text retrieval to select evidence before writing the report."
            if retrieval_backed
            else (
                "This deterministic MVP validates the run lifecycle before real retrieval, "
                "LLM reasoning, and LangGraph orchestration are connected."
            )
        )
        executive_summary = (
            "ResearchOS retrieved local document evidence and generated a grounded report.\n"
            if retrieval_backed
            else "ResearchOS MVP completed a deterministic evidence-first run loop.\n"
        )
        markdown = self._build_markdown(run, source, evidence, claim, verification, summary)
        report_json = {
            "run_id": run.run_id,
            "title": "ResearchOS MVP Run Report",
            "summary": summary,
            "claims": [claim.model_dump(mode="json")],
            "evidence": [evidence.model_dump(mode="json")],
            "sources": [source.model_dump(mode="json")],
            "citations": [verification.model_dump(mode="json")],
            "limitations": [
                "This MVP report is generated from one selected evidence chunk.",
                "Future versions should use multiple sources, conflict checks, and LLM review.",
            ],
        }
        return ReportDraft(
            markdown=markdown,
            report_json=report_json,
            executive_summary=executive_summary,
        )

    def _build_markdown(
        self,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
        summary: str,
    ) -> str:
        citation_label = f"{source.source_id}:{evidence.evidence_id}"
        return "\n".join(
            [
                "# ResearchOS MVP Run Report",
                "",
                f"Run ID: `{run.run_id}`",
                f"Query: {run.query}",
                "",
                "## Summary",
                "",
                summary,
                "",
                "## Evidence",
                "",
                f"- Source: {source.title} (`{source.source_id}`)",
                f"- Evidence: {evidence.text}",
                f"- Citation: `{citation_label}`",
                "",
                "## Claim Verification",
                "",
                f"- Claim: {claim.text}",
                f"- Status: {verification.support_status}",
                f"- Rationale: {verification.rationale}",
                f"- Confidence: {verification.confidence:.2f}",
                "",
                "## Limitations",
                "",
                "- This MVP report uses one selected evidence chunk.",
                "- Future versions should use multiple sources and conflict checks.",
                "",
            ]
        )
