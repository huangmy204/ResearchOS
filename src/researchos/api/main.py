from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from researchos.api.routes_artifacts import router as artifacts_router
from researchos.api.routes_evidence import router as evidence_router
from researchos.api.routes_health import router as health_router
from researchos.api.routes_models import router as models_router
from researchos.api.routes_runs import router as runs_router
from researchos.api.routes_trace import router as trace_router
from researchos.api.services import build_services
from researchos.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="ResearchOS",
        description="Evidence-first, run-oriented Deep Research Agent runtime.",
        version="0.1.0",
    )
    app.state.services = build_services(resolved_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(models_router)
    app.include_router(evidence_router)
    app.include_router(artifacts_router)
    app.include_router(trace_router)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "researchos.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.runtime_profile == "developer",
    )
