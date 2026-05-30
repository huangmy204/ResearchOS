from __future__ import annotations

from researchos.llm import LLMProviderError, LLMResponse
from researchos.models.evidence import Claim, Evidence
from researchos.models_router import ModelProfile
from researchos.retrieval import RetrievedChunk
from researchos.verification import LLMCitationVerifier, RuleBasedCitationVerifier


class JSONLLMClient:
    def __init__(self, content: str):
        self.content = content

    def complete(self, request):
        return LLMResponse(
            content=self.content,
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=10,
            completion_tokens=12,
            total_tokens=22,
            dry_run=False,
        )


class FailingLLMClient:
    def complete(self, request):
        raise LLMProviderError("provider failed")


def test_rule_based_citation_verifier_supports_retrieved_chunk():
    verifier = RuleBasedCitationVerifier()

    result = verifier.verify(
        claim=_claim(),
        evidence=_evidence(),
        retrieved_chunk=_chunk(),
    )

    assert result.support_status == "supported"
    assert result.verification_id == "ver_local_001"
    assert result.confidence == 0.8


def test_llm_citation_verifier_uses_structured_json_response():
    verifier = LLMCitationVerifier(
        llm_client=JSONLLMClient(
            
                '{"support_status":"partially_supported",'
                '"rationale":"Evidence overlaps but is narrow.",'
                '"confidence":0.62}'
            
        ),
        verifier_profile=_profile(),
    )

    result = verifier.verify(
        claim=_claim(),
        evidence=_evidence(),
        retrieved_chunk=_chunk(),
    )

    assert result.verification_id == "ver_local_001_llm"
    assert result.support_status == "partially_supported"
    assert result.rationale == "Evidence overlaps but is narrow."
    assert result.confidence == 0.62


def test_llm_citation_verifier_accepts_json_code_fence():
    verifier = LLMCitationVerifier(
        llm_client=JSONLLMClient(
            
                '```json\n{"support_status":"supported",'
                '"rationale":"Direct support.","confidence":0.91}\n```'
            
        ),
        verifier_profile=_profile(),
    )

    result = verifier.verify(
        claim=_claim(),
        evidence=_evidence(),
        retrieved_chunk=_chunk(),
    )

    assert result.support_status == "supported"
    assert result.rationale == "Direct support."
    assert result.confidence == 0.91


def test_llm_citation_verifier_falls_back_on_provider_error():
    verifier = LLMCitationVerifier(
        llm_client=FailingLLMClient(),
        verifier_profile=_profile(),
    )

    result = verifier.verify(
        claim=_claim(),
        evidence=_evidence(),
        retrieved_chunk=_chunk(),
    )

    assert result.support_status == "supported"
    assert result.verification_id == "ver_local_001"
    assert "LLM verifier fallback" in result.rationale
    assert "provider failed" in result.rationale


def _profile() -> ModelProfile:
    return ModelProfile(
        role="verifier",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        provider="openai_compatible",
        configured=True,
    )


def _claim() -> Claim:
    return Claim(
        claim_id="claim_local_001",
        run_id="run_test",
        text="The document discusses citation risk.",
        claim_type="analysis",
        evidence_ids=["ev_local_001"],
        confidence=0.8,
        verification_status="supported",
    )


def _evidence() -> Evidence:
    return Evidence(
        evidence_id="ev_local_001",
        source_id="src_doc_001",
        run_id="run_test",
        text="Unsupported citations create legal research risk.",
        extraction_method="parser",
        confidence=0.9,
    )


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_index=0,
        title="Legal AI memo",
        text="Unsupported citations create legal research risk.",
        score=0.8,
    )
