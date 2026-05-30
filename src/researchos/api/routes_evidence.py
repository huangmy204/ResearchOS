from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.evidence import (
    CitationVerification,
    Claim,
    Evidence,
    EvidenceBundleResponse,
    EvidenceGraph,
    Source,
)

router = APIRouter(prefix="/v1/research-runs", tags=["evidence"])


@router.get("/{run_id}/evidence", response_model=EvidenceBundleResponse)
def get_evidence_bundle(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> EvidenceBundleResponse:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")

    try:
        sources = services.artifact_store.read_json(run, "evidence/sources.json")
        evidence = services.artifact_store.read_json(run, "evidence/evidence.json")
        claims = services.artifact_store.read_json(run, "evidence/claims.json")
        citation_verification = services.artifact_store.read_json(
            run, "evidence/citation_verification.json"
        )
        evidence_graph = services.artifact_store.read_json(run, "evidence/evidence_graph.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Evidence artifacts not found.") from exc

    return EvidenceBundleResponse(
        run_id=run.run_id,
        sources=[Source.model_validate(item) for item in sources],
        evidence=[Evidence.model_validate(item) for item in evidence],
        claims=[Claim.model_validate(item) for item in claims],
        citation_verification=[
            CitationVerification.model_validate(item) for item in citation_verification
        ],
        evidence_graph=EvidenceGraph.model_validate(evidence_graph),
    )


@router.get("/{run_id}/evidence/graph", response_model=EvidenceGraph)
def get_evidence_graph(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> EvidenceGraph:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")

    try:
        evidence_graph = services.artifact_store.read_json(run, "evidence/evidence_graph.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Evidence graph not found.") from exc
    return EvidenceGraph.model_validate(evidence_graph)
