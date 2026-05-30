from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.llm import LLMMessage, LLMRequest, LLMResponse
from researchos.models_router import ModelProfile
from researchos.models_router.router import ModelRole

router = APIRouter(prefix="/v1/models", tags=["models"])


class ModelProfilesResponse(BaseModel):
    profiles: list[ModelProfile]


class ModelDryRunRequest(BaseModel):
    role: ModelRole
    prompt: str = Field(min_length=1)


class ModelDryRunResponse(BaseModel):
    profile: ModelProfile
    response: LLMResponse


@router.get("", response_model=ModelProfilesResponse)
def list_model_profiles(
    services: Annotated[AppServices, Depends(get_services)],
) -> ModelProfilesResponse:
    return ModelProfilesResponse(profiles=services.model_router.list_profiles())


@router.post("/dry-run", response_model=ModelDryRunResponse)
def dry_run_model_completion(
    request: ModelDryRunRequest,
    services: Annotated[AppServices, Depends(get_services)],
) -> ModelDryRunResponse:
    profile = services.model_router.select(request.role)
    llm_request = LLMRequest(
        profile=profile,
        messages=[
            LLMMessage(
                role="system",
                content=f"You are the ResearchOS {request.role} agent.",
            ),
            LLMMessage(role="user", content=request.prompt),
        ],
    )
    response = services.llm_client.complete(llm_request)
    return ModelDryRunResponse(profile=profile, response=response)
