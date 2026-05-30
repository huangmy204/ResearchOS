from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from researchos.llm import LLMClient, LLMClientError, LLMMessage, LLMRequest
from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun
from researchos.models_router import ModelProfile


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


class LLMReportWriter:
    def __init__(
        self,
        *,
        llm_client: LLMClient,
        writer_profile: ModelProfile,
        fallback_writer: ReportWriter | None = None,
    ):
        self.llm_client = llm_client
        self.writer_profile = writer_profile
        self.fallback_writer = fallback_writer or EvidenceReportWriter()

    def write(
        self,
        *,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
    ) -> ReportDraft:
        fallback = self.fallback_writer.write(
            run=run,
            source=source,
            evidence=evidence,
            claim=claim,
            verification=verification,
        )

        try:
            response = self.llm_client.complete(
                LLMRequest(
                    profile=self.writer_profile,
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You are the report writer for ResearchOS. "
                                "Write concise, evidence-grounded markdown. "
                                "Do not invent sources. Keep the citation label exactly as given."
                            ),
                        ),
                        LLMMessage(
                            role="user",
                            content=self._build_prompt(run, source, evidence, claim, verification),
                        ),
                    ],
                    temperature=0.2,
                    max_tokens=900,
                )
            )
        except LLMClientError as exc:
            fallback.report_json["generation"] = {
                "mode": "fallback",
                "reason": str(exc),
            }
            return fallback

        markdown = self._wrap_llm_markdown(run, response.content)
        report_json = {
            **fallback.report_json,
            "title": "ResearchOS LLM Run Report",
            "summary": response.content[:500],
            "generation": {
                "mode": "llm",
                "model": response.model,
                "provider": response.provider,
                "dry_run": response.dry_run,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
        }
        executive_summary = self._build_executive_summary(response.content)
        return ReportDraft(
            markdown=markdown,
            report_json=report_json,
            executive_summary=executive_summary,
        )

    def _build_prompt(
        self,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
    ) -> str:
        citation_label = f"{source.source_id}:{evidence.evidence_id}"
        return "\n".join(
            [
                f"Research question: {run.query}",
                "",
                "Use this exact markdown structure:",
                "# ResearchOS LLM Run Report",
                "## Summary",
                "## Evidence",
                "## Claim Verification",
                "## Limitations",
                "",
                "Grounding data:",
                f"- Source title: {source.title}",
                f"- Source id: {source.source_id}",
                f"- Evidence id: {evidence.evidence_id}",
                f"- Evidence text: {evidence.text}",
                f"- Required citation label: `{citation_label}`",
                f"- Claim: {claim.text}",
                f"- Verification status: {verification.support_status}",
                f"- Verification rationale: {verification.rationale}",
                "",
                "Rules:",
                "- Cite the evidence using the required citation label.",
                "- Mention uncertainty or limitations clearly.",
                "- Do not add unsupported facts.",
            ]
        )

    def _wrap_llm_markdown(self, run: ResearchRun, content: str) -> str:
        return "\n".join(
            [
                content.strip(),
                "",
                "---",
                "",
                f"Run ID: `{run.run_id}`",
                "Generated by: `llm_writer`",
                "",
            ]
        )

    def _build_executive_summary(self, content: str) -> str:
        first_non_empty_line = next(
            (line.strip("# ").strip() for line in content.splitlines() if line.strip()),
            "ResearchOS generated an LLM-assisted evidence report.",
        )
        return f"{first_non_empty_line}\n"
