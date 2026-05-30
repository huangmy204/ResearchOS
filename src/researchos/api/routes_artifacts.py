from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.artifact import ArtifactListResponse

router = APIRouter(prefix="/v1/research-runs", tags=["artifacts"])


@router.get("/{run_id}/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> ArtifactListResponse:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return ArtifactListResponse(artifacts=services.artifact_store.list(run))


@router.get("/{run_id}/artifacts/content")
def get_artifact_content(
    run_id: str,
    path: Annotated[str, Query(min_length=1)],
    services: Annotated[AppServices, Depends(get_services)],
) -> Response:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    try:
        content, mime_type = services.artifact_store.read_text(run, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found.") from exc
    return Response(content=content, media_type=mime_type)
