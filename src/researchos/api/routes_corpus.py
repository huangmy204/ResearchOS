from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.corpus import (
    CorpusDocumentCreate,
    CorpusDocumentResponse,
    CorpusFile,
    CorpusIndexResponse,
    CorpusListResponse,
)

router = APIRouter(prefix="/v1/corpus", tags=["corpus"])


@router.get("", response_model=CorpusListResponse)
def list_corpus_files(
    services: Annotated[AppServices, Depends(get_services)],
) -> CorpusListResponse:
    files = services.corpus_loader.list_files()
    return CorpusListResponse(
        corpus_root=str(services.corpus_loader.corpus_root),
        files=[
            CorpusFile(
                path=file.path,
                title=file.title,
                size_bytes=file.size_bytes,
                suffix=file.suffix,
            )
            for file in files
        ],
    )


@router.get("/content", response_model=CorpusDocumentResponse)
def get_corpus_document(
    path: Annotated[str, Query(min_length=1)],
    services: Annotated[AppServices, Depends(get_services)],
) -> CorpusDocumentResponse:
    try:
        document = services.corpus_loader.read_document(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Corpus document not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(document)


@router.post("/documents", response_model=CorpusDocumentResponse, status_code=201)
def create_corpus_document(
    request: CorpusDocumentCreate,
    services: Annotated[AppServices, Depends(get_services)],
) -> CorpusDocumentResponse:
    try:
        document = services.corpus_loader.write_document(
            title=request.title,
            text=request.text,
            relative_path=request.path,
            overwrite=request.overwrite,
        )
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail="Corpus document already exists. Set overwrite=true to replace it.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _document_response(document)


@router.get("/index", response_model=CorpusIndexResponse)
def get_corpus_index(
    services: Annotated[AppServices, Depends(get_services)],
) -> CorpusIndexResponse:
    return _index_response(services.corpus_index.read())


@router.post("/index", response_model=CorpusIndexResponse)
def build_corpus_index(
    services: Annotated[AppServices, Depends(get_services)],
) -> CorpusIndexResponse:
    return _index_response(services.corpus_index.build())


def _document_response(document) -> CorpusDocumentResponse:
    return CorpusDocumentResponse(
        path=document.path,
        title=document.title,
        text=document.text,
        size_bytes=document.size_bytes,
        suffix=document.suffix,
    )


def _index_response(manifest) -> CorpusIndexResponse:
    return CorpusIndexResponse(
        version=manifest.version,
        corpus_root=manifest.corpus_root,
        indexed_at=manifest.indexed_at,
        document_count=manifest.document_count,
        entries=[
            {
                "path": entry.path,
                "title": entry.title,
                "size_bytes": entry.size_bytes,
                "suffix": entry.suffix,
                "modified_at": entry.modified_at,
                "content_sha256": entry.content_sha256,
                "status": entry.status,
            }
            for entry in manifest.entries
        ],
    )
