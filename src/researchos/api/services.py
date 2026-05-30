from __future__ import annotations

from dataclasses import dataclass

from researchos.config import Settings
from researchos.runtime import ResearchWorkflow
from researchos.stores import ArtifactStore, EventStore, RunStore, Workspace


@dataclass
class AppServices:
    settings: Settings
    workspace: Workspace
    run_store: RunStore
    event_store: EventStore
    artifact_store: ArtifactStore
    workflow: ResearchWorkflow


def build_services(settings: Settings) -> AppServices:
    workspace = Workspace(settings.workspace_root)
    workspace.initialize()
    run_store = RunStore(workspace)
    event_store = EventStore(workspace)
    artifact_store = ArtifactStore(workspace)
    workflow = ResearchWorkflow(run_store, event_store, artifact_store)
    return AppServices(
        settings=settings,
        workspace=workspace,
        run_store=run_store,
        event_store=event_store,
        artifact_store=artifact_store,
        workflow=workflow,
    )
