from __future__ import annotations

from dataclasses import dataclass

from researchos.config import Settings
from researchos.llm import LLMClient, MockLLMClient, OpenAICompatibleLLMClient
from researchos.models_router import ModelRouter
from researchos.planning import LLMResearchPlanner, ResearchPlanner, StaticResearchPlanner
from researchos.reporting import EvidenceReportWriter, LLMReportWriter, ReportWriter
from researchos.retrieval.factory import build_retriever
from researchos.runtime import (
    LangGraphWorkflowEngine,
    ResearchWorkflow,
    SequentialWorkflowEngine,
    WorkflowEngine,
)
from researchos.stores import ArtifactStore, EventStore, RunStore, Workspace
from researchos.verification import CitationVerifier, LLMCitationVerifier, RuleBasedCitationVerifier


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
    research_planner = build_research_planner(settings, model_router, llm_client)
    report_writer = build_report_writer(settings, model_router, llm_client)
    citation_verifier = build_citation_verifier(settings, model_router, llm_client)
    workflow_engine = build_workflow_engine(settings, run_store, event_store, artifact_store)
    workflow = ResearchWorkflow(
        run_store,
        event_store,
        artifact_store,
        retriever=build_retriever(
            settings.retrieval_strategy,
            max_chunk_chars=settings.retrieval_chunk_chars,
            chunk_overlap_chars=settings.retrieval_chunk_overlap_chars,
        ),
        research_planner=research_planner,
        report_writer=report_writer,
        citation_verifier=citation_verifier,
        engine=workflow_engine,
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


def build_workflow_engine(
    settings: Settings,
    run_store: RunStore,
    event_store: EventStore,
    artifact_store: ArtifactStore,
) -> WorkflowEngine:
    engine_name = settings.workflow_engine.strip().lower()
    if engine_name == "sequential":
        return SequentialWorkflowEngine(
            run_store=run_store,
            event_store=event_store,
            artifact_store=artifact_store,
        )
    if engine_name == "langgraph":
        return LangGraphWorkflowEngine(
            run_store=run_store,
            event_store=event_store,
            artifact_store=artifact_store,
        )
    supported = "sequential, langgraph"
    raise ValueError(
        f"Unsupported workflow engine '{settings.workflow_engine}'. Use one of: {supported}."
    )


def build_research_planner(
    settings: Settings,
    model_router: ModelRouter,
    llm_client: LLMClient,
) -> ResearchPlanner:
    fallback_planner = StaticResearchPlanner()
    if settings.llm_client == "openai_compatible":
        return LLMResearchPlanner(
            llm_client=llm_client,
            planner_profile=model_router.select("planner"),
            fallback_planner=fallback_planner,
        )
    return fallback_planner


def build_report_writer(
    settings: Settings,
    model_router: ModelRouter,
    llm_client: LLMClient,
) -> ReportWriter:
    fallback_writer = EvidenceReportWriter()
    if settings.llm_client == "openai_compatible":
        return LLMReportWriter(
            llm_client=llm_client,
            writer_profile=model_router.select("writer"),
            fallback_writer=fallback_writer,
        )
    return fallback_writer


def build_citation_verifier(
    settings: Settings,
    model_router: ModelRouter,
    llm_client: LLMClient,
) -> CitationVerifier:
    fallback_verifier = RuleBasedCitationVerifier()
    if settings.llm_client == "openai_compatible":
        return LLMCitationVerifier(
            llm_client=llm_client,
            verifier_profile=model_router.select("verifier"),
            fallback_verifier=fallback_verifier,
        )
    return fallback_verifier
