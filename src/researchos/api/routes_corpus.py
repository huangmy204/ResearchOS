from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from researchos.api.deps import get_services
from researchos.api.services import AppServices
from researchos.models.corpus import CorpusFile, CorpusListResponse

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
