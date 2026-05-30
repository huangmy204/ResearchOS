from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.llm import (
    LLMConfigurationError,
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    MockLLMClient,
)
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


class ModelCompletionRequest(BaseModel):
    role: ModelRole
    prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class ModelCompletionResponse(BaseModel):
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
    response = MockLLMClient().complete(llm_request)
    return ModelDryRunResponse(profile=profile, response=response)


@router.post("/complete", response_model=ModelCompletionResponse)
def complete_with_model(
    request: ModelCompletionRequest,
    services: Annotated[AppServices, Depends(get_services)],
) -> ModelCompletionResponse:
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
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    try:
        response = services.llm_client.complete(llm_request)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ModelCompletionResponse(profile=profile, response=response)
