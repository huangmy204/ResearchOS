from __future__ import annotations

from datetime import UTC, datetime

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun
from researchos.models_router import ModelProfile
from researchos.reporting import EvidenceReportWriter, LLMReportWriter


class StaticLLMClient:
    def complete(self, request):
        from researchos.llm import LLMResponse

        return LLMResponse(
            content=(
                "# ResearchOS LLM Run Report\n\n"
                "## Summary\n\n"
                "The evidence supports the citation risk finding.\n\n"
                "## Evidence\n\n"
                "Citation: `src_doc_001:ev_local_001`\n\n"
                "## Claim Verification\n\n"
                "The claim is supported.\n\n"
                "## Limitations\n\n"
                "Only one evidence chunk was used."
            ),
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50,
            dry_run=False,
        )


class FailingLLMClient:
    def complete(self, request):
        from researchos.llm import LLMProviderError

        raise LLMProviderError("provider unavailable")


def test_evidence_report_writer_builds_cited_markdown_and_json():
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="writing",
        query="legal citation risk",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    source = Source(
        source_id="src_doc_001",
        run_id=run.run_id,
        source_type="file",
        title="Legal AI memo",
        retrieved_at=datetime.now(UTC),
        relevance_score=0.9,
    )
    evidence = Evidence(
        evidence_id="ev_local_001",
        source_id=source.source_id,
        run_id=run.run_id,
        text="Unsupported citations create legal research risk.",
        extraction_method="parser",
        confidence=0.9,
    )
    claim = Claim(
        claim_id="claim_local_001",
        run_id=run.run_id,
        text="Local documents contain citation risk evidence.",
        claim_type="analysis",
        evidence_ids=[evidence.evidence_id],
        confidence=0.9,
        verification_status="supported",
    )
    verification = CitationVerification(
        verification_id="ver_local_001",
        claim_id=claim.claim_id,
        evidence_id=evidence.evidence_id,
        support_status="supported",
        rationale="The evidence directly mentions citation risk.",
        confidence=0.9,
    )

    draft = EvidenceReportWriter().write(
        run=run,
        source=source,
        evidence=evidence,
        claim=claim,
        verification=verification,
    )

    assert "Citation: `src_doc_001:ev_local_001`" in draft.markdown
    assert "Unsupported citations create legal research risk." in draft.markdown
    assert draft.report_json["claims"][0]["claim_id"] == claim.claim_id
    assert draft.report_json["citations"][0]["support_status"] == "supported"
    assert "grounded report" in draft.executive_summary


def test_llm_report_writer_uses_model_response():
    run, source, evidence, claim, verification = _build_report_inputs()
    writer = LLMReportWriter(
        llm_client=StaticLLMClient(),
        writer_profile=ModelProfile(
            role="writer",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="openai_compatible",
            configured=True,
        ),
    )

    draft = writer.write(
        run=run,
        source=source,
        evidence=evidence,
        claim=claim,
        verification=verification,
    )

    assert "ResearchOS LLM Run Report" in draft.markdown
    assert "Citation: `src_doc_001:ev_local_001`" in draft.markdown
    assert draft.report_json["generation"]["mode"] == "llm"
    assert draft.report_json["generation"]["model"] == "qwen-plus"
    assert draft.report_json["generation"]["total_tokens"] == 50


def test_llm_report_writer_falls_back_when_provider_fails():
    run, source, evidence, claim, verification = _build_report_inputs()
    writer = LLMReportWriter(
        llm_client=FailingLLMClient(),
        writer_profile=ModelProfile(
            role="writer",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="openai_compatible",
            configured=True,
        ),
    )

    draft = writer.write(
        run=run,
        source=source,
        evidence=evidence,
        claim=claim,
        verification=verification,
    )

    assert "ResearchOS MVP Run Report" in draft.markdown
    assert draft.report_json["generation"]["mode"] == "fallback"
    assert "provider unavailable" in draft.report_json["generation"]["reason"]


def _build_report_inputs():
    run = ResearchRun(
        run_id="run_test",
        session_id="session",
        status="writing",
        query="legal citation risk",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    source = Source(
        source_id="src_doc_001",
        run_id=run.run_id,
        source_type="file",
        title="Legal AI memo",
        retrieved_at=datetime.now(UTC),
        relevance_score=0.9,
    )
    evidence = Evidence(
        evidence_id="ev_local_001",
        source_id=source.source_id,
        run_id=run.run_id,
        text="Unsupported citations create legal research risk.",
        extraction_method="parser",
        confidence=0.9,
    )
    claim = Claim(
        claim_id="claim_local_001",
        run_id=run.run_id,
        text="Local documents contain citation risk evidence.",
        claim_type="analysis",
        evidence_ids=[evidence.evidence_id],
        confidence=0.9,
        verification_status="supported",
    )
    verification = CitationVerification(
        verification_id="ver_local_001",
        claim_id=claim.claim_id,
        evidence_id=evidence.evidence_id,
        support_status="supported",
        rationale="The evidence directly mentions citation risk.",
        confidence=0.9,
    )
    return run, source, evidence, claim, verification
