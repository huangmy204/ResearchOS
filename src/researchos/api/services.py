from __future__ import annotations

from dataclasses import dataclass

from researchos.config import Settings
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
    workflow: ResearchWorkflow


def build_services(settings: Settings) -> AppServices:
    workspace = Workspace(settings.workspace_root)
    workspace.initialize()
    run_store = RunStore(workspace)
    event_store = EventStore(workspace)
    artifact_store = ArtifactStore(workspace)
    model_router = ModelRouter(settings)
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
        workflow=workflow,
    )
