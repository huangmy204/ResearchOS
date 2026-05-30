from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.event import ResearchEventListResponse
from researchos.models.run import (
    ResearchRun,
    ResearchRunCreate,
    ResearchRunCreateResponse,
    ResearchRunListResponse,
)

router = APIRouter(prefix="/v1/research-runs", tags=["research-runs"])


@router.post("", response_model=ResearchRunCreateResponse, status_code=201)
async def create_research_run(
    request: ResearchRunCreate,
    services: Annotated[AppServices, Depends(get_services)],
) -> ResearchRunCreateResponse:
    existing = services.run_store.find_by_request_id(request)
    if existing is not None:
        return _create_response(existing)

    run = services.run_store.create(request)
    services.event_store.append(run, "run.created", {"run_id": run.run_id, "query": run.query})
    asyncio.create_task(services.workflow.run(run.run_id))
    return _create_response(run)


@router.get("", response_model=ResearchRunListResponse)
def list_research_runs(
    services: Annotated[AppServices, Depends(get_services)],
) -> ResearchRunListResponse:
    return ResearchRunListResponse(runs=services.run_store.list_all())


def _create_response(run: ResearchRun) -> ResearchRunCreateResponse:
    return ResearchRunCreateResponse(
        run_id=run.run_id,
        status=run.status,
        events_url=f"/v1/research-runs/{run.run_id}/events",
        artifacts_url=f"/v1/research-runs/{run.run_id}/artifacts",
    )


@router.get("/{run_id}", response_model=ResearchRun)
def get_research_run(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> ResearchRun:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return run


@router.get("/{run_id}/events/history", response_model=ResearchEventListResponse)
def list_research_run_events(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> ResearchEventListResponse:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return ResearchEventListResponse(events=services.event_store.list(run))


@router.post("/{run_id}/cancel", response_model=ResearchRun)
def cancel_research_run(
    run_id: str,
    services: Annotated[AppServices, Depends(get_services)],
) -> ResearchRun:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")
    if run.status in {"completed", "failed", "cancelled"}:
        return run
    cancelled = services.run_store.update(
        run_id,
        status="cancelled",
        current_step="cancelled",
        finished=True,
    )
    services.event_store.append(cancelled, "run.cancelled", {"run_id": run_id})
    return cancelled


@router.get("/{run_id}/events")
async def stream_research_run_events(
    run_id: str,
    request: Request,
    services: Annotated[AppServices, Depends(get_services)],
) -> StreamingResponse:
    run = services.run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found.")

    async def event_generator():
        last_sequence = 0
        while True:
            current = services.run_store.get(run_id)
            if current is None:
                break

            events = services.event_store.list(current, after_sequence=last_sequence)
            for event in events:
                last_sequence = event.sequence
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.event_type}\n"
                    f"data: {event.model_dump_json()}\n\n"
                )

            if current.status in {"completed", "failed", "cancelled"}:
                break
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.25)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
