from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.ingestion import LoadedCorpus
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
    try:
        loaded_corpus = _load_requested_corpus(request, services)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request = _merge_corpus_documents(request, loaded_corpus)
    existing = services.run_store.find_by_request_id(request)
    if existing is not None:
        return _create_response(existing)

    run = services.run_store.create(request)
    services.event_store.append(run, "run.created", {"run_id": run.run_id, "query": run.query})
    if loaded_corpus.files:
        services.artifact_store.write_json(
            run,
            "inputs/corpus_manifest.json",
            {
                "run_id": run.run_id,
                "document_count": len(loaded_corpus.documents),
                "files": [
                    {
                        "path": file.path,
                        "title": file.title,
                        "size_bytes": file.size_bytes,
                    }
                    for file in loaded_corpus.files
                ],
            },
        )
        services.event_store.append(
            run,
            "corpus.loaded",
            {
                "run_id": run.run_id,
                "document_count": len(loaded_corpus.documents),
            },
        )
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


def _load_requested_corpus(
    request: ResearchRunCreate,
    services: AppServices,
) -> LoadedCorpus:
    include_corpus = bool(request.options.get("include_corpus", False))
    corpus_paths = request.options.get("corpus_paths")
    if corpus_paths is not None and not isinstance(corpus_paths, list):
        raise ValueError("options.corpus_paths must be a list of relative paths.")
    if corpus_paths is not None and not all(isinstance(path, str) for path in corpus_paths):
        raise ValueError("options.corpus_paths must contain only strings.")
    if not include_corpus and not corpus_paths:
        return LoadedCorpus(documents=[], files=[])
    return services.corpus_loader.load(relative_paths=corpus_paths)


def _merge_corpus_documents(
    request: ResearchRunCreate,
    loaded_corpus: LoadedCorpus,
) -> ResearchRunCreate:
    if not loaded_corpus.documents:
        return request
    return request.model_copy(
        update={"documents": [*request.documents, *loaded_corpus.documents]}
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
