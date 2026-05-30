from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from researchos.config import Settings

ModelRole = Literal["basic", "planner", "searcher", "reader", "writer", "verifier", "reviewer"]


class ModelProfile(BaseModel):
    role: ModelRole
    model: str
    base_url: str = ""
    provider: str = "unconfigured"
    configured: bool = False


class ModelRouter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def select(self, role: ModelRole) -> ModelProfile:
        if role in {"planner", "reviewer"}:
            return self._profile(
                role,
                self.settings.reasoning_model,
                self.settings.reasoning_base_url,
            )
        if role == "writer":
            return self._profile(role, self.settings.writer_model, self.settings.writer_base_url)
        if role == "verifier":
            return self._profile(
                role,
                self.settings.verifier_model,
                self.settings.verifier_base_url,
            )
        return self._profile(role, self.settings.basic_model, self.settings.basic_base_url)

    def list_profiles(self) -> list[ModelProfile]:
        roles: list[ModelRole] = [
            "basic",
            "planner",
            "searcher",
            "reader",
            "writer",
            "verifier",
            "reviewer",
        ]
        return [self.select(role) for role in roles]

    def _profile(self, role: ModelRole, model: str, base_url: str) -> ModelProfile:
        return ModelProfile(
            role=role,
            model=model,
            base_url=base_url,
            provider=self._infer_provider(base_url),
            configured=bool(model),
        )

    def _infer_provider(self, base_url: str) -> str:
        if not base_url:
            return "unconfigured"
        if "openai.com" in base_url:
            return "openai"
        return "openai_compatible"
