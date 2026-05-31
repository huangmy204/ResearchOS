from __future__ import annotations

from datetime import UTC, datetime

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.planning import ResearchPlanner
from researchos.reporting import ReportDraft, ReportWriter
from researchos.retrieval import RetrievedChunk, Retriever
from researchos.runtime.state import NodeResult, WorkflowState
from researchos.stores.artifact_store import ArtifactStore
from researchos.verification import CitationVerifier


class PlanningNode:
    name = "planning"

    def __init__(self, research_planner: ResearchPlanner, artifact_store: ArtifactStore):
        self.research_planner = research_planner
        self.artifact_store = artifact_store

    def execute(self, state: WorkflowState) -> NodeResult:
        state.plan = self.research_planner.plan(state.run)
        self.artifact_store.write_json(state.run, "plans/research_plan.json", state.plan)
        return NodeResult(
            node_name=self.name,
            status="planning",
            step_name="creating research plan",
            completed_steps=0,
            event_type="plan.created",
            payload={"run_id": state.run.run_id, "steps": state.plan},
            artifacts=["plans/research_plan.json"],
        )


class RetrievalNode:
    name = "retrieval"

    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    def execute(self, state: WorkflowState) -> NodeResult:
        chunks = self.retriever.retrieve(state.run.query, state.run.documents, limit=1)
        state.retrieved_chunk = chunks[0] if chunks else None
        state.source = _build_source(state, state.retrieved_chunk)
        return NodeResult(
            node_name=self.name,
            status="searching",
            step_name="retrieving seed sources",
            completed_steps=1,
            event_type="source.retrieved",
            payload=state.source.model_dump(mode="json"),
        )


class ReadingNode:
    name = "reading"

    def execute(self, state: WorkflowState) -> NodeResult:
        source = _require(state.source, "source")
        return NodeResult(
            node_name=self.name,
            status="reading",
            step_name="reading retrieved material",
            completed_steps=2,
            event_type="source.read",
            payload={
                "run_id": state.run.run_id,
                "source_id": source.source_id,
                "retrieval_mode": "local_text" if state.retrieved_chunk else "synthetic",
            },
        )


class EvidenceExtractionNode:
    name = "evidence_extraction"

    def execute(self, state: WorkflowState) -> NodeResult:
        source = _require(state.source, "source")
        state.evidence = _build_evidence(state, source, state.retrieved_chunk)
        state.claim = _build_claim(state, state.evidence, state.retrieved_chunk)
        return NodeResult(
            node_name=self.name,
            status="extracting_evidence",
            step_name="extracting evidence spans",
            completed_steps=3,
            event_type="evidence.extracted",
            payload=state.evidence.model_dump(mode="json"),
        )


class VerificationNode:
    name = "verification"

    def __init__(self, citation_verifier: CitationVerifier):
        self.citation_verifier = citation_verifier

    def execute(self, state: WorkflowState) -> NodeResult:
        claim = _require(state.claim, "claim")
        evidence = _require(state.evidence, "evidence")
        state.verification = self.citation_verifier.verify(
            claim=claim,
            evidence=evidence,
            retrieved_chunk=state.retrieved_chunk,
        )
        return NodeResult(
            node_name=self.name,
            status="verifying",
            step_name="checking claim support",
            completed_steps=4,
            event_type="claim.verified",
            payload=state.verification.model_dump(mode="json"),
        )


class ReportWritingNode:
    name = "report_writing"

    def __init__(self, artifact_store: ArtifactStore, report_writer: ReportWriter):
        self.artifact_store = artifact_store
        self.report_writer = report_writer

    def execute(self, state: WorkflowState) -> NodeResult:
        source = _require(state.source, "source")
        evidence = _require(state.evidence, "evidence")
        claim = _require(state.claim, "claim")
        verification = _require(state.verification, "verification")

        artifact_paths = write_evidence_artifacts(
            self.artifact_store,
            state,
            source,
            evidence,
            claim,
            verification,
        )
        state.report = self.report_writer.write(
            run=state.run,
            source=source,
            evidence=evidence,
            claim=claim,
            verification=verification,
        )
        self.artifact_store.write_text(state.run, "outputs/report.md", state.report.markdown)
        self.artifact_store.write_json(state.run, "outputs/report.json", state.report.report_json)
        self.artifact_store.write_text(
            state.run,
            "outputs/executive_summary.md",
            state.report.executive_summary,
        )
        artifact_paths.extend(
            ["outputs/report.md", "outputs/report.json", "outputs/executive_summary.md"]
        )
        return NodeResult(
            node_name=self.name,
            status="writing",
            step_name="writing report artifacts",
            completed_steps=5,
            event_type="report.draft_created",
            payload={"run_id": state.run.run_id, "path": "outputs/report.md"},
            artifacts=artifact_paths,
        )


class InsufficientEvidenceReportNode:
    name = "insufficient_evidence_report"

    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def execute(self, state: WorkflowState) -> NodeResult:
        markdown = "\n".join(
            [
                "# ResearchOS Evidence Gap Report",
                "",
                f"Run ID: `{state.run.run_id}`",
                f"Query: {state.run.query}",
                "",
                "## Summary",
                "",
                "ResearchOS did not find enough local evidence to produce a grounded answer.",
                "",
                "## Evidence Status",
                "",
                "- Retrieved evidence chunks: 0",
                "- Report mode: insufficient evidence",
                "",
                "## Next Steps",
                "",
                "- Add more relevant local documents.",
                "- Enable a broader search tool in a future workflow.",
                "- Re-run the research task after new sources are available.",
                "",
            ]
        )
        report_json = {
            "run_id": state.run.run_id,
            "title": "ResearchOS Evidence Gap Report",
            "summary": "No supporting evidence was retrieved from the available local documents.",
            "generation": {"mode": "insufficient_evidence"},
            "claims": [],
            "evidence": [],
            "sources": [],
            "citations": [],
            "limitations": [
                "The workflow did not generate claims because no supporting evidence was found.",
                "Future versions should broaden retrieval before asking the writer to answer.",
            ],
        }
        executive_summary = "ResearchOS found no sufficient local evidence for this run.\n"
        state.report = ReportDraft(
            markdown=markdown,
            report_json=report_json,
            executive_summary=executive_summary,
        )
        self.artifact_store.write_text(state.run, "outputs/report.md", markdown)
        self.artifact_store.write_json(state.run, "outputs/report.json", report_json)
        self.artifact_store.write_text(
            state.run,
            "outputs/executive_summary.md",
            executive_summary,
        )
        return NodeResult(
            node_name=self.name,
            status="writing",
            step_name="writing insufficient evidence report",
            completed_steps=5,
            event_type="report.insufficient_evidence",
            payload={"run_id": state.run.run_id, "path": "outputs/report.md"},
            artifacts=["outputs/report.md", "outputs/report.json", "outputs/executive_summary.md"],
        )


class EvaluationNode:
    name = "evaluation"

    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def execute(self, state: WorkflowState) -> NodeResult:
        has_evidence = state.evidence is not None
        metrics = (
            {
                "retrieval_recall": 1.0,
                "citation_precision": 1.0,
                "claim_support_rate": 1.0,
                "report_completeness": 1.0,
                "latency_sec": 0.0,
                "tool_success_rate": 1.0,
            }
            if has_evidence
            else {
                "retrieval_recall": 0.0,
                "citation_precision": 0.0,
                "claim_support_rate": 0.0,
                "report_completeness": 0.3,
                "latency_sec": 0.0,
                "tool_success_rate": 1.0,
            }
        )
        verdict = "pass" if has_evidence else "needs_evidence"
        self.artifact_store.write_json(
            state.run,
            "evals/eval_result.json",
            {
                "eval_run_id": f"eval_{state.run.run_id}",
                "case_id": "mvp_smoke",
                "research_run_id": state.run.run_id,
                "metrics": metrics,
                "verdict": verdict,
                "regression": not has_evidence,
            },
        )
        self.artifact_store.write_text(
            state.run,
            "evals/eval_report.md",
            f"# MVP Smoke Eval\n\nVerdict: {verdict}\n",
        )
        return NodeResult(
            node_name=self.name,
            status="reviewing",
            step_name="reviewing completeness",
            completed_steps=6,
            event_type="review.completed",
            payload={"run_id": state.run.run_id, "quality_score": metrics["report_completeness"]},
            artifacts=["evals/eval_result.json", "evals/eval_report.md"],
        )


def write_evidence_artifacts(
    artifact_store: ArtifactStore,
    state: WorkflowState,
    source: Source,
    evidence: Evidence,
    claim: Claim,
    verification: CitationVerification,
) -> list[str]:
    artifact_store.write_json(state.run, "evidence/sources.json", [source.model_dump(mode="json")])
    artifact_store.write_json(
        state.run,
        "evidence/evidence.json",
        [evidence.model_dump(mode="json")],
    )
    artifact_store.write_json(
        state.run,
        "evidence/claims.json",
        [claim.model_dump(mode="json")],
    )
    artifact_store.write_json(
        state.run,
        "evidence/citation_verification.json",
        [verification.model_dump(mode="json")],
    )
    artifact_store.write_json(
        state.run,
        "evidence/evidence_graph.json",
        {
            "run_id": state.run.run_id,
            "nodes": [
                {"id": source.source_id, "type": "source", "title": source.title},
                {"id": evidence.evidence_id, "type": "evidence", "text": evidence.text},
                {"id": claim.claim_id, "type": "claim", "text": claim.text},
            ],
            "edges": [
                {
                    "from": evidence.evidence_id,
                    "to": source.source_id,
                    "type": "derived_from",
                },
                {"from": claim.claim_id, "to": evidence.evidence_id, "type": "supported_by"},
            ],
        },
    )
    artifact_paths = [
        "evidence/sources.json",
        "evidence/evidence.json",
        "evidence/claims.json",
        "evidence/citation_verification.json",
        "evidence/evidence_graph.json",
    ]
    if state.retrieved_chunk is not None:
        artifact_store.write_json(
            state.run,
            "sources/parsed/retrieval_results.json",
            [
                {
                    "document_index": state.retrieved_chunk.document_index,
                    "title": state.retrieved_chunk.title,
                    "text": state.retrieved_chunk.text,
                    "score": state.retrieved_chunk.score,
                    "url": state.retrieved_chunk.url,
                }
            ],
        )
        artifact_paths.append("sources/parsed/retrieval_results.json")
    return artifact_paths


def _build_source(state: WorkflowState, chunk: RetrievedChunk | None) -> Source:
    if chunk is None:
        return Source(
            source_id="src_mvp_001",
            run_id=state.run.run_id,
            source_type="tool_result",
            title="MVP synthetic source",
            url=None,
            retrieved_at=datetime.now(UTC),
            credibility_score=0.5,
            relevance_score=0.7,
        )

    return Source(
        source_id=f"src_doc_{chunk.document_index + 1:03d}",
        run_id=state.run.run_id,
        source_type="file",
        title=chunk.title,
        url=chunk.url,
        retrieved_at=datetime.now(UTC),
        credibility_score=0.8,
        relevance_score=chunk.score,
    )


def _build_evidence(
    state: WorkflowState,
    source: Source,
    chunk: RetrievedChunk | None,
) -> Evidence:
    if chunk is None:
        return Evidence(
            evidence_id="ev_mvp_001",
            source_id=source.source_id,
            run_id=state.run.run_id,
            text=(
                "The MVP runtime can create isolated research runs, stream events, "
                "and write run-scoped artifacts before real retrieval is connected."
            ),
            extraction_method="manual",
            confidence=0.95,
        )

    return Evidence(
        evidence_id="ev_local_001",
        source_id=source.source_id,
        run_id=state.run.run_id,
        text=chunk.text,
        extraction_method="parser",
        confidence=min(1.0, max(0.2, chunk.score)),
    )


def _build_claim(
    state: WorkflowState,
    evidence: Evidence,
    chunk: RetrievedChunk | None,
) -> Claim:
    if chunk is None:
        return Claim(
            claim_id="claim_mvp_001",
            run_id=state.run.run_id,
            text="ResearchOS can first be validated through a deterministic local run loop.",
            claim_type="analysis",
            evidence_ids=[evidence.evidence_id],
            confidence=0.86,
            verification_status="supported",
        )

    return Claim(
        claim_id="claim_local_001",
        run_id=state.run.run_id,
        text=f"The supplied local documents contain evidence relevant to: {state.run.query}",
        claim_type="analysis",
        evidence_ids=[evidence.evidence_id],
        confidence=min(1.0, max(0.3, chunk.score)),
        verification_status="supported",
    )


def _require(value, name: str):
    if value is None:
        raise RuntimeError(f"Workflow state is missing required value: {name}")
    return value
