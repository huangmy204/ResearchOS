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
    retrieval_strategy: str = "keyword"
    workflow_engine: str = "sequential"
    basic_model: str = ""
    basic_base_url: str = ""
    reasoning_model: str = ""
    reasoning_base_url: str = ""
    writer_model: str = ""
    writer_base_url: str = ""
    verifier_model: str = ""
    verifier_base_url: str = ""
    llm_client: str = "mock"
    llm_api_key: str = ""
    llm_timeout_sec: float = 30.0


def load_local_env(env_path: Path | None = None) -> bool:
    path = env_path or Path(".env")
    if not path.exists():
        return False

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
    return True


def get_settings() -> Settings:
    load_local_env()
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
        retrieval_strategy=os.getenv("RESEARCHOS_RETRIEVAL_STRATEGY", "keyword"),
        workflow_engine=os.getenv("RESEARCHOS_WORKFLOW_ENGINE", "sequential"),
        basic_model=os.getenv("BASIC_MODEL", ""),
        basic_base_url=os.getenv("BASIC_BASE_URL", ""),
        reasoning_model=os.getenv("REASONING_MODEL", ""),
        reasoning_base_url=os.getenv("REASONING_BASE_URL", ""),
        writer_model=os.getenv("WRITER_MODEL", ""),
        writer_base_url=os.getenv("WRITER_BASE_URL", ""),
        verifier_model=os.getenv("VERIFIER_MODEL", ""),
        verifier_base_url=os.getenv("VERIFIER_BASE_URL", ""),
        llm_client=os.getenv("RESEARCHOS_LLM_CLIENT", "mock"),
        llm_api_key=os.getenv("RESEARCHOS_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        llm_timeout_sec=float(os.getenv("RESEARCHOS_LLM_TIMEOUT_SEC", "30")),
    )
