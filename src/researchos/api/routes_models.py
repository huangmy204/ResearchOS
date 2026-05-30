from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models_router import ModelProfile

router = APIRouter(prefix="/v1/models", tags=["models"])


class ModelProfilesResponse(BaseModel):
    profiles: list[ModelProfile]


@router.get("", response_model=ModelProfilesResponse)
def list_model_profiles(
    services: Annotated[AppServices, Depends(get_services)],
) -> ModelProfilesResponse:
    return ModelProfilesResponse(profiles=services.model_router.list_profiles())
