from __future__ import annotations

from pathlib import Path

from researchos.config import Settings
from researchos.models_router import ModelRouter


def test_model_router_selects_role_specific_profiles():
    settings = Settings(
        env="test",
        workspace_root=Path("workspace"),
        runtime_profile="test",
        log_level="INFO",
        api_host="127.0.0.1",
        api_port=8000,
        cors_allow_origins=[],
        basic_model="fast-model",
        basic_base_url="https://api.openai.com/v1",
        reasoning_model="reasoning-model",
        writer_model="writer-model",
        verifier_model="verifier-model",
    )
    router = ModelRouter(settings)

    assert router.select("searcher").model == "fast-model"
    assert router.select("planner").model == "reasoning-model"
    assert router.select("reviewer").model == "reasoning-model"
    assert router.select("writer").model == "writer-model"
    assert router.select("verifier").model == "verifier-model"
    assert router.select("basic").provider == "openai"


def test_model_router_marks_missing_model_as_unconfigured():
    settings = Settings(
        env="test",
        workspace_root=Path("workspace"),
        runtime_profile="test",
        log_level="INFO",
        api_host="127.0.0.1",
        api_port=8000,
        cors_allow_origins=[],
    )
    router = ModelRouter(settings)

    profile = router.select("writer")

    assert profile.model == ""
    assert profile.provider == "unconfigured"
    assert profile.configured is False
