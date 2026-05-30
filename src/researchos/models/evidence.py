from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    source_id: str
    run_id: str
    source_type: Literal["web", "pdf", "file", "database", "tool_result"]
    title: str
    url: str | None = None
    local_path: str | None = None
    author: str | None = None
    published_at: str | None = None
    retrieved_at: datetime
    credibility_score: float | None = None
    relevance_score: float | None = None


class Evidence(BaseModel):
    evidence_id: str
    source_id: str
    run_id: str
    text: str
    start_offset: int | None = None
    end_offset: int | None = None
    page_number: int | None = None
    section_title: str | None = None
    extraction_method: Literal["llm", "regex", "parser", "manual"]
    confidence: float = Field(ge=0.0, le=1.0)


class Claim(BaseModel):
    claim_id: str
    run_id: str
    text: str
    claim_type: Literal["fact", "analysis", "prediction", "recommendation", "risk"]
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    verification_status: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
        "not_enough_information",
    ] = "not_enough_information"


class CitationVerification(BaseModel):
    verification_id: str
    claim_id: str
    evidence_id: str
    support_status: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
        "not_enough_information",
    ]
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceGraph(BaseModel):
    run_id: str
    nodes: list[dict]
    edges: list[dict]


class EvidenceBundleResponse(BaseModel):
    run_id: str
    sources: list[Source]
    evidence: list[Evidence]
    claims: list[Claim]
    citation_verification: list[CitationVerification]
    evidence_graph: EvidenceGraph
