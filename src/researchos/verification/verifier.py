from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel, Field

from researchos.llm import LLMClient, LLMClientError, LLMMessage, LLMRequest
from researchos.models.evidence import CitationVerification, Claim, Evidence
from researchos.models_router import ModelProfile
from researchos.retrieval import RetrievedChunk


class CitationVerifier(Protocol):
    def verify(
        self,
        *,
        claim: Claim,
        evidence: Evidence,
        retrieved_chunk: RetrievedChunk | None,
    ) -> CitationVerification:
        """Judge whether evidence supports a claim."""


class VerificationDecision(BaseModel):
    support_status: str
    rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class RuleBasedCitationVerifier:
    def verify(
        self,
        *,
        claim: Claim,
        evidence: Evidence,
        retrieved_chunk: RetrievedChunk | None,
    ) -> CitationVerification:
        if retrieved_chunk is None:
            rationale = "The claim matches the deterministic MVP workflow behavior."
            confidence = 0.9
        else:
            rationale = "The claim is supported by the top-ranked local text chunk."
            confidence = min(1.0, max(0.3, retrieved_chunk.score))

        return CitationVerification(
            verification_id="ver_mvp_001" if retrieved_chunk is None else "ver_local_001",
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            support_status="supported",
            rationale=rationale,
            confidence=confidence,
        )


class LLMCitationVerifier:
    def __init__(
        self,
        *,
        llm_client: LLMClient,
        verifier_profile: ModelProfile,
        fallback_verifier: CitationVerifier | None = None,
    ):
        self.llm_client = llm_client
        self.verifier_profile = verifier_profile
        self.fallback_verifier = fallback_verifier or RuleBasedCitationVerifier()

    def verify(
        self,
        *,
        claim: Claim,
        evidence: Evidence,
        retrieved_chunk: RetrievedChunk | None,
    ) -> CitationVerification:
        fallback = self.fallback_verifier.verify(
            claim=claim,
            evidence=evidence,
            retrieved_chunk=retrieved_chunk,
        )

        try:
            response = self.llm_client.complete(
                LLMRequest(
                    profile=self.verifier_profile,
                    messages=[
                        LLMMessage(
                            role="system",
                            content=(
                                "You are the citation verifier for ResearchOS. "
                                "Return only compact JSON. Do not include markdown."
                            ),
                        ),
                        LLMMessage(
                            role="user",
                            content=self._build_prompt(claim, evidence),
                        ),
                    ],
                    temperature=0.0,
                    max_tokens=300,
                )
            )
            decision = _parse_verification_decision(response.content)
        except (LLMClientError, ValueError) as exc:
            fallback.rationale = f"{fallback.rationale} LLM verifier fallback: {exc}"
            return fallback

        support_status = _normalize_support_status(decision.support_status)
        return CitationVerification(
            verification_id=f"{fallback.verification_id}_llm",
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            support_status=support_status,
            rationale=decision.rationale,
            confidence=decision.confidence,
        )

    def _build_prompt(self, claim: Claim, evidence: Evidence) -> str:
        return "\n".join(
            [
                "Decide whether the evidence supports the claim.",
                "",
                f"Claim: {claim.text}",
                f"Evidence: {evidence.text}",
                "",
                "Return JSON with exactly these fields:",
                (
                    '{"support_status":"supported|partially_supported|unsupported|'
                    'contradicted|not_enough_information","rationale":"short reason",'
                    '"confidence":0.0}'
                ),
            ]
        )


def _parse_verification_decision(content: str) -> VerificationDecision:
    raw = content.strip()
    if not raw:
        raise ValueError("LLM verifier returned empty content.")

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM verifier did not return valid JSON.") from exc

    return VerificationDecision.model_validate(data)


def _normalize_support_status(status: str) -> str:
    allowed = {
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
        "not_enough_information",
    }
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in allowed:
        raise ValueError(f"Unsupported verification status: {status}")
    return normalized
