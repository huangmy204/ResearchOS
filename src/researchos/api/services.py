from __future__ import annotations

from dataclasses import dataclass

from researchos.config import Settings
from researchos.llm import LLMClient, MockLLMClient, OpenAICompatibleLLMClient
from researchos.models_router import ModelRouter
from researchos.reporting import EvidenceReportWriter
from researchos.retrieval.factory import build_retriever
from researchos.runtime import ResearchWorkflow
from researchos.stores import ArtifactStore, EventStore, RunStore, Workspace


@dataclass
class AppServices:
    settings: Settings
    workspace: Workspace
    run_store: RunStore
    event_store: EventStore
    artifact_store: ArtifactStore
    model_router: ModelRouter
    llm_client: LLMClient
    workflow: ResearchWorkflow


def build_services(settings: Settings) -> AppServices:
    workspace = Workspace(settings.workspace_root)
    workspace.initialize()
    run_store = RunStore(workspace)
    event_store = EventStore(workspace)
    artifact_store = ArtifactStore(workspace)
    model_router = ModelRouter(settings)
    llm_client = build_llm_client(settings)
    workflow = ResearchWorkflow(
        run_store,
        event_store,
        artifact_store,
        retriever=build_retriever(settings.retrieval_strategy),
        report_writer=EvidenceReportWriter(),
    )
    return AppServices(
        settings=settings,
        workspace=workspace,
        run_store=run_store,
        event_store=event_store,
        artifact_store=artifact_store,
        model_router=model_router,
        llm_client=llm_client,
        workflow=workflow,
    )


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_client == "openai_compatible":
        return OpenAICompatibleLLMClient(
            api_key=settings.llm_api_key,
            timeout_sec=settings.llm_timeout_sec,
        )
    return MockLLMClient()
