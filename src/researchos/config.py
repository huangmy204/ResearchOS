from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    workspace_root: Path
    runtime_profile: str
    log_level: str
    api_host: str
    api_port: int
    cors_allow_origins: list[str]


def get_settings() -> Settings:
    workspace_root = Path(os.getenv("RESEARCHOS_WORKSPACE_ROOT", "workspace"))
    origins = os.getenv("RESEARCHOS_CORS_ALLOW_ORIGINS", "http://localhost:3000")
    return Settings(
        env=os.getenv("RESEARCHOS_ENV", "development"),
        workspace_root=workspace_root,
        runtime_profile=os.getenv("RESEARCHOS_RUNTIME_PROFILE", "developer"),
        log_level=os.getenv("RESEARCHOS_LOG_LEVEL", "INFO"),
        api_host=os.getenv("RESEARCHOS_API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("RESEARCHOS_API_PORT", "8000")),
        cors_allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    )
