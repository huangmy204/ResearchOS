from __future__ import annotations

from datetime import UTC, datetime

from researchos.evals.metrics import build_workflow_eval_result
from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.planning import ResearchPlanner
from researchos.reporting import ReportDraft, ReportWriter
from researchos.retrieval import (
    NoopReranker,
    Reranker,
    RetrievedChunk,
    Retriever,
    SourceDiversityPolicy,
)
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

    def __init__(
        self,
        retriever: Retriever,
        artifact_store: ArtifactStore,
        *,
        reranker: Reranker | None = None,
        diversity_policy: SourceDiversityPolicy | None = None,
        top_k: int = 3,
        candidate_limit: int = 6,
        min_evidence_count: int = 1,
    ):
        self.retriever = retriever
        self.artifact_store = artifact_store
        self.reranker = reranker or NoopReranker()
        self.diversity_policy = diversity_policy or SourceDiversityPolicy()
        self.top_k = top_k
        self.candidate_limit = candidate_limit
        self.min_evidence_count = min_evidence_count

    def execute(self, state: WorkflowState) -> NodeResult:
        candidate_limit = max(self.candidate_limit, self.top_k)
        candidates = self.retriever.retrieve(
            state.run.query,
            state.run.documents,
            limit=candidate_limit,
        )
        reranked_candidates = self.reranker.rerank(
            state.run.query,
            candidates,
            limit=candidate_limit,
        )
        chunks = self.diversity_policy.select(reranked_candidates, limit=self.top_k)
        state.retrieved_chunks = chunks
        state.retrieved_chunk = chunks[0] if chunks else None
        state.retrieval_quality = _build_retrieval_quality(
            chunks,
            min_evidence_count=self.min_evidence_count,
        )
        state.sources = (
            [_build_source(state, chunk, index) for index, chunk in enumerate(chunks)]
            if chunks
            else [_build_source(state, None, 0)]
        )
        state.source = state.sources[0]
        diagnostics = _build_retrieval_diagnostics(
            state,
            self.retriever,
            self.reranker,
            self.diversity_policy,
            candidates,
            reranked_candidates,
            chunks,
            candidate_limit=candidate_limit,
            top_k=self.top_k,
            quality_gate=state.retrieval_quality,
        )
        self.artifact_store.write_json(
            state.run,
            "sources/retrieval_diagnostics.json",
            diagnostics,
        )
        return NodeResult(
            node_name=self.name,
            status="searching",
            step_name="retrieving seed sources",
            completed_steps=1,
            event_type="source.retrieved",
            payload={
                "run_id": state.run.run_id,
                "retrieved_count": len(chunks),
                "strategy": diagnostics["strategy"],
                "sources": [source.model_dump(mode="json") for source in state.sources],
            },
            artifacts=["sources/retrieval_diagnostics.json"],
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
        sources = state.sources or [_require(state.source, "source")]
        chunks = state.retrieved_chunks or [state.retrieved_chunk]
        state.evidence_items = [
            _build_evidence(state, source, chunks[index], index)
            for index, source in enumerate(sources)
        ]
        state.claims = [
            _build_claim(state, evidence, chunks[index], index)
            for index, evidence in enumerate(state.evidence_items)
        ]
        state.evidence = state.evidence_items[0]
        state.claim = state.claims[0]
        return NodeResult(
            node_name=self.name,
            status="extracting_evidence",
            step_name="extracting evidence spans",
            completed_steps=3,
            event_type="evidence.extracted",
            payload={
                "run_id": state.run.run_id,
                "evidence": [
                    evidence.model_dump(mode="json") for evidence in state.evidence_items
                ],
            },
        )


class VerificationNode:
    name = "verification"

    def __init__(self, citation_verifier: CitationVerifier):
        self.citation_verifier = citation_verifier

    def execute(self, state: WorkflowState) -> NodeResult:
        claims = state.claims or [_require(state.claim, "claim")]
        evidence_items = state.evidence_items or [_require(state.evidence, "evidence")]
        chunks = state.retrieved_chunks or [state.retrieved_chunk]
        state.verifications = []
        for index, claim in enumerate(claims):
            verification = self.citation_verifier.verify(
                claim=claim,
                evidence=evidence_items[index],
                retrieved_chunk=chunks[index],
            )
            verification.verification_id = _verification_id(verification.verification_id, index)
            state.verifications.append(verification)
        state.verification = state.verifications[0]
        return NodeResult(
            node_name=self.name,
            status="verifying",
            step_name="checking claim support",
            completed_steps=4,
            event_type="claim.verified",
            payload={
                "run_id": state.run.run_id,
                "verifications": [
                    verification.model_dump(mode="json")
                    for verification in state.verifications
                ],
            },
        )


class ReportWritingNode:
    name = "report_writing"

    def __init__(self, artifact_store: ArtifactStore, report_writer: ReportWriter):
        self.artifact_store = artifact_store
        self.report_writer = report_writer

    def execute(self, state: WorkflowState) -> NodeResult:
        sources = state.sources or [_require(state.source, "source")]
        evidence_items = state.evidence_items or [_require(state.evidence, "evidence")]
        claims = state.claims or [_require(state.claim, "claim")]
        verifications = state.verifications or [_require(state.verification, "verification")]

        artifact_paths = write_evidence_artifacts(
            self.artifact_store,
            state,
            sources,
            evidence_items,
            claims,
            verifications,
        )
        state.report = self.report_writer.write(
            run=state.run,
            source=sources[0],
            evidence=evidence_items[0],
            claim=claims[0],
            verification=verifications[0],
            sources=sources,
            evidence_items=evidence_items,
            claims=claims,
            verifications=verifications,
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
            "retrieval_quality": state.retrieval_quality,
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
        diagnostics = _read_json_artifact(
            self.artifact_store,
            state,
            "sources/retrieval_diagnostics.json",
        )
        report_json = (
            state.report.report_json
            if state.report is not None
            else _read_json_artifact(self.artifact_store, state, "outputs/report.json")
        )
        eval_result = build_workflow_eval_result(
            run=state.run,
            diagnostics=diagnostics,
            sources=state.sources,
            evidence_items=state.evidence_items,
            claims=state.claims,
            verifications=state.verifications,
            report_json=report_json if isinstance(report_json, dict) else None,
        )
        self.artifact_store.write_json(
            state.run,
            "evals/eval_result.json",
            eval_result,
        )
        self.artifact_store.write_text(
            state.run,
            "evals/eval_report.md",
            _build_workflow_eval_report(eval_result),
        )
        return NodeResult(
            node_name=self.name,
            status="reviewing",
            step_name="reviewing completeness",
            completed_steps=6,
            event_type="review.completed",
            payload={
                "run_id": state.run.run_id,
                "quality_score": eval_result["metrics"]["report_completeness"],
                "verdict": eval_result["verdict"],
            },
            artifacts=["evals/eval_result.json", "evals/eval_report.md"],
        )


def write_evidence_artifacts(
    artifact_store: ArtifactStore,
    state: WorkflowState,
    sources: list[Source],
    evidence_items: list[Evidence],
    claims: list[Claim],
    verifications: list[CitationVerification],
) -> list[str]:
    artifact_store.write_json(
        state.run,
        "evidence/sources.json",
        [source.model_dump(mode="json") for source in sources],
    )
    artifact_store.write_json(
        state.run,
        "evidence/evidence.json",
        [evidence.model_dump(mode="json") for evidence in evidence_items],
    )
    artifact_store.write_json(
        state.run,
        "evidence/claims.json",
        [claim.model_dump(mode="json") for claim in claims],
    )
    artifact_store.write_json(
        state.run,
        "evidence/citation_verification.json",
        [verification.model_dump(mode="json") for verification in verifications],
    )
    artifact_store.write_json(
        state.run,
        "evidence/evidence_graph.json",
        {
            "run_id": state.run.run_id,
            "nodes": _evidence_graph_nodes(sources, evidence_items, claims),
            "edges": _evidence_graph_edges(sources, evidence_items, claims),
        },
    )
    artifact_paths = [
        "evidence/sources.json",
        "evidence/evidence.json",
        "evidence/claims.json",
        "evidence/citation_verification.json",
        "evidence/evidence_graph.json",
    ]
    if state.retrieved_chunks:
        artifact_store.write_json(
            state.run,
            "sources/parsed/retrieval_results.json",
            [
                {
                    "rank": index + 1,
                    "document_index": chunk.document_index,
                    "title": chunk.title,
                    "text": chunk.text,
                    "score": chunk.score,
                    "url": chunk.url,
                }
                for index, chunk in enumerate(state.retrieved_chunks)
            ],
        )
        artifact_paths.append("sources/parsed/retrieval_results.json")
    return artifact_paths


def _build_retrieval_diagnostics(
    state: WorkflowState,
    retriever: Retriever,
    reranker: Reranker,
    diversity_policy: SourceDiversityPolicy,
    candidates: list[RetrievedChunk],
    reranked_candidates: list[RetrievedChunk],
    chunks: list[RetrievedChunk],
    *,
    candidate_limit: int,
    top_k: int,
    quality_gate: dict,
) -> dict:
    return {
        "run_id": state.run.run_id,
        "query": state.run.query,
        "strategy": getattr(retriever, "strategy_name", retriever.__class__.__name__),
        "score_type": getattr(retriever, "score_type", "unknown"),
        "candidate_limit": candidate_limit,
        "top_k": top_k,
        "document_count": len(state.run.documents),
        "candidate_count": len(candidates),
        "retrieved_count": len(chunks),
        "quality_gate": quality_gate,
        "source_diversity": {
            "enabled": diversity_policy.enabled,
            "max_chunks_per_source": diversity_policy.max_chunks_per_source,
            "selected_source_count": len({chunk.document_index for chunk in chunks}),
        },
        "reranker": {
            "name": getattr(reranker, "name", reranker.__class__.__name__),
            "score_type": getattr(reranker, "score_type", "unknown"),
            "applied": getattr(reranker, "name", "") != "none",
        },
        "chunking": {
            "max_chunk_chars": getattr(retriever, "max_chunk_chars", None),
            "chunk_overlap_chars": getattr(retriever, "chunk_overlap_chars", None),
        },
        "candidates": [
            _retrieval_diagnostic_result(candidate, retriever, index)
            for index, candidate in enumerate(candidates)
        ],
        "reranked_candidates": [
            _retrieval_diagnostic_result(candidate, retriever, index)
            for index, candidate in enumerate(reranked_candidates)
        ],
        "results": [
            _retrieval_diagnostic_result(chunk, retriever, index)
            for index, chunk in enumerate(chunks)
        ],
    }


def _build_retrieval_quality(
    chunks: list[RetrievedChunk],
    *,
    min_evidence_count: int,
) -> dict:
    retrieved_count = len(chunks)
    passed = retrieved_count >= min_evidence_count
    return {
        "passed": passed,
        "min_evidence_count": min_evidence_count,
        "retrieved_count": retrieved_count,
        "reason": (
            "enough_evidence"
            if passed
            else f"retrieved_count_below_minimum:{retrieved_count}<{min_evidence_count}"
        ),
    }


def _retrieval_diagnostic_result(
    chunk: RetrievedChunk,
    retriever: Retriever,
    index: int,
) -> dict:
    return {
        "rank": index + 1,
        "document_index": chunk.document_index,
        "title": chunk.title,
        "score": chunk.score,
        "score_type": getattr(retriever, "score_type", "unknown"),
        "text_chars": len(chunk.text),
        "url": chunk.url,
    }


def _read_json_artifact(
    artifact_store: ArtifactStore,
    state: WorkflowState,
    logical_path: str,
) -> object | None:
    try:
        return artifact_store.read_json(state.run, logical_path)
    except FileNotFoundError:
        return None


def _build_workflow_eval_report(eval_result: dict) -> str:
    lines = [
        "# MVP Smoke Eval",
        "",
        f"Verdict: {eval_result['verdict']}",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(
        f"- {name}: {value:.4f}"
        for name, value in eval_result["metrics"].items()
    )
    lines.extend(
        [
            "",
            "## Retrieval",
            "",
            f"- Strategy: {eval_result['dimensions']['retrieval'].get('strategy')}",
            f"- Top K: {eval_result['dimensions']['retrieval'].get('top_k')}",
            (
                "- Reranker: "
                f"{eval_result['dimensions']['retrieval'].get('reranker', {}).get('name')}"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _build_source(state: WorkflowState, chunk: RetrievedChunk | None, index: int) -> Source:
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

    source_id = f"src_doc_{chunk.document_index + 1:03d}"
    if index > 0:
        source_id = f"{source_id}_{index + 1:03d}"
    return Source(
        source_id=source_id,
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
    index: int,
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
        evidence_id=f"ev_local_{index + 1:03d}",
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
    index: int,
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
        claim_id=f"claim_local_{index + 1:03d}",
        run_id=state.run.run_id,
        text=(
            "A supplied local document contains evidence relevant to "
            f"'{state.run.query}' from chunk {index + 1}."
        ),
        claim_type="analysis",
        evidence_ids=[evidence.evidence_id],
        confidence=min(1.0, max(0.3, chunk.score)),
        verification_status="supported",
    )


def _verification_id(base_id: str, index: int) -> str:
    if index == 0:
        return base_id
    return f"{base_id}_{index + 1:03d}"


def _evidence_graph_nodes(
    sources: list[Source],
    evidence_items: list[Evidence],
    claims: list[Claim],
) -> list[dict]:
    return [
        *[
            {"id": source.source_id, "type": "source", "title": source.title}
            for source in sources
        ],
        *[
            {"id": evidence.evidence_id, "type": "evidence", "text": evidence.text}
            for evidence in evidence_items
        ],
        *[{"id": claim.claim_id, "type": "claim", "text": claim.text} for claim in claims],
    ]


def _evidence_graph_edges(
    sources: list[Source],
    evidence_items: list[Evidence],
    claims: list[Claim],
) -> list[dict]:
    edges: list[dict] = []
    for source, evidence, claim in zip(sources, evidence_items, claims, strict=True):
        edges.append(
            {
                "from": evidence.evidence_id,
                "to": source.source_id,
                "type": "derived_from",
            }
        )
        edges.append(
            {
                "from": claim.claim_id,
                "to": evidence.evidence_id,
                "type": "supported_by",
            }
        )
    return edges


def _require(value, name: str):
    if value is None:
        raise RuntimeError(f"Workflow state is missing required value: {name}")
    return value
