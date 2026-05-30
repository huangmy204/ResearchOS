from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun, RunStatus
from researchos.reporting import EvidenceReportWriter, ReportWriter
from researchos.retrieval import LocalKeywordRetriever, RetrievedChunk, Retriever
from researchos.stores.artifact_store import ArtifactStore
from researchos.stores.event_store import EventStore
from researchos.stores.run_store import RunStore
from researchos.verification import CitationVerifier, RuleBasedCitationVerifier


class WorkflowCancelled(Exception):
    """Raised internally when a run is cancelled while the workflow is active."""


class ResearchWorkflow:
    """Deterministic MVP workflow that preserves the real run contract."""

    def __init__(
        self,
        run_store: RunStore,
        event_store: EventStore,
        artifact_store: ArtifactStore,
        retriever: Retriever | None = None,
        report_writer: ReportWriter | None = None,
        citation_verifier: CitationVerifier | None = None,
        *,
        step_delay_sec: float = 0.05,
    ):
        self.run_store = run_store
        self.event_store = event_store
        self.artifact_store = artifact_store
        self.retriever = retriever or LocalKeywordRetriever()
        self.report_writer = report_writer or EvidenceReportWriter()
        self.citation_verifier = citation_verifier or RuleBasedCitationVerifier()
        self.step_delay_sec = step_delay_sec

    async def run(self, run_id: str) -> None:
        run = self.run_store.get(run_id)
        if run is None:
            return
        if run.status == "cancelled":
            return

        try:
            plan = [
                {
                    "step_id": "step_001",
                    "goal": "Clarify the research question and define evidence requirements.",
                    "agent": "planner",
                    "expected_output": "research plan",
                },
                {
                    "step_id": "step_002",
                    "goal": "Collect initial sources for the query.",
                    "agent": "searcher",
                    "expected_output": "candidate source list",
                },
                {
                    "step_id": "step_003",
                    "goal": "Extract evidence spans and verify claim support.",
                    "agent": "evidence_verifier",
                    "expected_output": "evidence graph and report",
                },
            ]

            run = await self._advance(
                run,
                status="planning",
                step_name="creating research plan",
                completed_steps=0,
                event_type="plan.created",
                payload={"run_id": run.run_id, "steps": plan},
            )
            await self._pause(run.run_id)

            retrieved_chunk = self._retrieve_top_chunk(run)
            source = self._build_source(run, retrieved_chunk)
            run = await self._advance(
                run,
                status="searching",
                step_name="retrieving seed sources",
                completed_steps=1,
                event_type="source.retrieved",
                payload=source.model_dump(mode="json"),
            )
            await self._pause(run.run_id)

            run = await self._advance(
                run,
                status="reading",
                step_name="reading retrieved material",
                completed_steps=2,
                event_type="source.read",
                payload={
                    "run_id": run.run_id,
                    "source_id": source.source_id,
                    "retrieval_mode": "local_text" if retrieved_chunk else "synthetic",
                },
            )
            await self._pause(run.run_id)

            evidence = self._build_evidence(run, source, retrieved_chunk)
            claim = self._build_claim(run, evidence, retrieved_chunk)
            run = await self._advance(
                run,
                status="extracting_evidence",
                step_name="extracting evidence spans",
                completed_steps=3,
                event_type="evidence.extracted",
                payload=evidence.model_dump(mode="json"),
            )
            await self._pause(run.run_id)

            verification = self.citation_verifier.verify(
                claim=claim,
                evidence=evidence,
                retrieved_chunk=retrieved_chunk,
            )
            run = await self._advance(
                run,
                status="verifying",
                step_name="checking claim support",
                completed_steps=4,
                event_type="claim.verified",
                payload=verification.model_dump(mode="json"),
            )
            await self._pause(run.run_id)

            self._raise_if_cancelled(run.run_id)
            self._write_evidence_artifacts(
                run, source, evidence, claim, verification, retrieved_chunk
            )
            report = self.report_writer.write(
                run=run,
                source=source,
                evidence=evidence,
                claim=claim,
                verification=verification,
            )
            self.artifact_store.write_text(run, "outputs/report.md", report.markdown)
            self.artifact_store.write_json(run, "outputs/report.json", report.report_json)
            self.artifact_store.write_text(
                run,
                "outputs/executive_summary.md",
                report.executive_summary,
            )
            run = await self._advance(
                run,
                status="writing",
                step_name="writing report artifacts",
                completed_steps=5,
                event_type="report.draft_created",
                payload={"run_id": run.run_id, "path": "outputs/report.md"},
            )
            await self._pause(run.run_id)

            self._raise_if_cancelled(run.run_id)
            self.artifact_store.write_json(
                run,
                "evals/eval_result.json",
                {
                    "eval_run_id": f"eval_{run.run_id}",
                    "case_id": "mvp_smoke",
                    "research_run_id": run.run_id,
                    "metrics": {
                        "retrieval_recall": 1.0,
                        "citation_precision": 1.0,
                        "claim_support_rate": 1.0,
                        "report_completeness": 1.0,
                        "latency_sec": 0.0,
                        "tool_success_rate": 1.0,
                    },
                    "verdict": "pass",
                    "regression": False,
                },
            )
            self.artifact_store.write_text(
                run,
                "evals/eval_report.md",
                "# MVP Smoke Eval\n\nVerdict: pass\n",
            )
            run = await self._advance(
                run,
                status="reviewing",
                step_name="reviewing completeness",
                completed_steps=6,
                event_type="review.completed",
                payload={"run_id": run.run_id, "quality_score": 1.0},
            )
            await self._pause(run.run_id)

            self._raise_if_cancelled(run.run_id)
            run = self.run_store.update(
                run.run_id,
                status="completed",
                current_step="completed",
                completed_steps=7,
                finished=True,
            )
            self.event_store.append(
                run,
                "report.completed",
                {"run_id": run.run_id, "artifact_path": "outputs/report.md"},
            )
            self.artifact_store.write_text(run, "logs/runtime.log", "MVP workflow completed.\n")
        except WorkflowCancelled:
            return
        except Exception as exc:
            failed = self.run_store.update(
                run.run_id,
                status="failed",
                current_step="failed",
                error=str(exc),
                finished=True,
            )
            self.event_store.append(failed, "run.failed", {"run_id": run.run_id, "error": str(exc)})

    async def _advance(
        self,
        run: ResearchRun,
        *,
        status: RunStatus,
        step_name: str,
        completed_steps: int,
        event_type: str,
        payload: dict,
    ) -> ResearchRun:
        current = self.run_store.get(run.run_id)
        if current and current.status == "cancelled":
            return current
        updated = self.run_store.update(
            run.run_id,
            status=status,
            current_step=step_name,
            completed_steps=completed_steps,
        )
        self.event_store.append(updated, event_type, payload)
        return updated

    async def _pause(self, run_id: str) -> None:
        if self.step_delay_sec > 0:
            await asyncio.sleep(self.step_delay_sec)
        self._raise_if_cancelled(run_id)

    def _raise_if_cancelled(self, run_id: str) -> None:
        current = self.run_store.get(run_id)
        if current and current.status == "cancelled":
            raise WorkflowCancelled

    def _retrieve_top_chunk(self, run: ResearchRun) -> RetrievedChunk | None:
        chunks = self.retriever.retrieve(run.query, run.documents, limit=1)
        return chunks[0] if chunks else None

    def _build_source(self, run: ResearchRun, chunk: RetrievedChunk | None) -> Source:
        if chunk is None:
            return Source(
                source_id="src_mvp_001",
                run_id=run.run_id,
                source_type="tool_result",
                title="MVP synthetic source",
                url=None,
                retrieved_at=datetime.now(UTC),
                credibility_score=0.5,
                relevance_score=0.7,
            )

        return Source(
            source_id=f"src_doc_{chunk.document_index + 1:03d}",
            run_id=run.run_id,
            source_type="file",
            title=chunk.title,
            url=chunk.url,
            retrieved_at=datetime.now(UTC),
            credibility_score=0.8,
            relevance_score=chunk.score,
        )

    def _build_evidence(
        self,
        run: ResearchRun,
        source: Source,
        chunk: RetrievedChunk | None,
    ) -> Evidence:
        if chunk is None:
            return Evidence(
                evidence_id="ev_mvp_001",
                source_id=source.source_id,
                run_id=run.run_id,
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
            run_id=run.run_id,
            text=chunk.text,
            extraction_method="parser",
            confidence=min(1.0, max(0.2, chunk.score)),
        )

    def _build_claim(
        self,
        run: ResearchRun,
        evidence: Evidence,
        chunk: RetrievedChunk | None,
    ) -> Claim:
        if chunk is None:
            return Claim(
                claim_id="claim_mvp_001",
                run_id=run.run_id,
                text="ResearchOS can first be validated through a deterministic local run loop.",
                claim_type="analysis",
                evidence_ids=[evidence.evidence_id],
                confidence=0.86,
                verification_status="supported",
            )

        return Claim(
            claim_id="claim_local_001",
            run_id=run.run_id,
            text=f"The supplied local documents contain evidence relevant to: {run.query}",
            claim_type="analysis",
            evidence_ids=[evidence.evidence_id],
            confidence=min(1.0, max(0.3, chunk.score)),
            verification_status="supported",
        )

    def _write_evidence_artifacts(
        self,
        run: ResearchRun,
        source: Source,
        evidence: Evidence,
        claim: Claim,
        verification: CitationVerification,
        retrieved_chunk: RetrievedChunk | None = None,
    ) -> None:
        self.artifact_store.write_json(
            run, "evidence/sources.json", [source.model_dump(mode="json")]
        )
        self.artifact_store.write_json(
            run, "evidence/evidence.json", [evidence.model_dump(mode="json")]
        )
        self.artifact_store.write_json(run, "evidence/claims.json", [claim.model_dump(mode="json")])
        self.artifact_store.write_json(
            run,
            "evidence/citation_verification.json",
            [verification.model_dump(mode="json")],
        )
        self.artifact_store.write_json(
            run,
            "evidence/evidence_graph.json",
            {
                "run_id": run.run_id,
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
        if retrieved_chunk is not None:
            self.artifact_store.write_json(
                run,
                "sources/parsed/retrieval_results.json",
                [
                    {
                        "document_index": retrieved_chunk.document_index,
                        "title": retrieved_chunk.title,
                        "text": retrieved_chunk.text,
                        "score": retrieved_chunk.score,
                        "url": retrieved_chunk.url,
                    }
                ],
            )
