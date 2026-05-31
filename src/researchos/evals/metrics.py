from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean
from typing import Any

from researchos.models.evidence import CitationVerification, Claim, Evidence, Source
from researchos.models.run import ResearchRun


def build_workflow_eval_result(
    *,
    run: ResearchRun,
    diagnostics: dict[str, Any] | None,
    sources: list[Source],
    evidence_items: list[Evidence],
    claims: list[Claim],
    verifications: list[CitationVerification],
    report_json: dict | None,
) -> dict:
    metrics = build_quality_metrics(
        diagnostics=diagnostics,
        sources=[source.model_dump(mode="json") for source in sources],
        evidence_items=[evidence.model_dump(mode="json") for evidence in evidence_items],
        claims=[claim.model_dump(mode="json") for claim in claims],
        verifications=[
            verification.model_dump(mode="json") for verification in verifications
        ],
        report_json=report_json,
        run_status="completed",
    )
    verdict = verdict_from_metrics(metrics)
    return {
        "eval_run_id": f"eval_{run.run_id}",
        "case_id": "mvp_smoke",
        "research_run_id": run.run_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "dimensions": {
            "retrieval": build_retrieval_dimension(diagnostics),
            "evidence": {
                "source_count": float(len(sources)),
                "evidence_count": float(len(evidence_items)),
                "claim_count": float(len(claims)),
                "verification_count": float(len(verifications)),
            },
            "report": {
                "generation_mode": _nested_get(report_json, ["generation", "mode"], "rule_based"),
                "has_report": float(report_json is not None),
            },
        },
        "verdict": verdict,
        "regression": verdict != "pass",
    }


def build_quality_metrics(
    *,
    diagnostics: dict[str, Any] | None,
    sources: list[dict],
    evidence_items: list[dict],
    claims: list[dict],
    verifications: list[dict],
    report_json: dict | None,
    run_status: str,
) -> dict[str, float]:
    retrieval_metrics = retrieval_metrics_from_diagnostics(diagnostics)
    citation_precision = score_citation_precision(verifications)
    claim_support_rate = score_claim_support_rate(claims)
    report_completeness = score_report_artifact_completeness(report_json)
    tool_success_rate = 1.0 if run_status == "completed" else 0.0

    metrics = {
        "retrieval_recall": retrieval_metrics["retrieval_recall"],
        "citation_precision": citation_precision,
        "claim_support_rate": claim_support_rate,
        "report_completeness": report_completeness,
        "latency_sec": 0.0,
        "estimated_cost": 0.0,
        "tool_success_rate": tool_success_rate,
        "retrieved_count": retrieval_metrics["retrieved_count"],
        "candidate_count": retrieval_metrics["candidate_count"],
        "evidence_count": float(len(evidence_items)),
        "source_count": float(len(sources)),
        "source_diversity_ratio": retrieval_metrics["source_diversity_ratio"],
        "average_retrieval_score": retrieval_metrics["average_retrieval_score"],
        "max_retrieval_score": retrieval_metrics["max_retrieval_score"],
        "min_retrieval_score": retrieval_metrics["min_retrieval_score"],
        "reranker_applied": retrieval_metrics["reranker_applied"],
        "source_diversity_enabled": retrieval_metrics["source_diversity_enabled"],
    }
    return {name: round(value, 4) for name, value in metrics.items()}


def retrieval_metrics_from_diagnostics(diagnostics: dict[str, Any] | None) -> dict[str, float]:
    if not diagnostics:
        return {
            "retrieval_recall": 0.0,
            "retrieved_count": 0.0,
            "candidate_count": 0.0,
            "source_diversity_ratio": 0.0,
            "average_retrieval_score": 0.0,
            "max_retrieval_score": 0.0,
            "min_retrieval_score": 0.0,
            "reranker_applied": 0.0,
            "source_diversity_enabled": 0.0,
        }

    results = diagnostics.get("results") if isinstance(diagnostics, dict) else []
    results = results if isinstance(results, list) else []
    scores = [float(item.get("score", 0.0)) for item in results if isinstance(item, dict)]
    document_indexes = {
        item.get("document_index") for item in results if isinstance(item, dict)
    }
    retrieved_count = float(len(results))
    selected_source_count = float(len(document_indexes))
    diversity = selected_source_count / retrieved_count if retrieved_count else 0.0
    reranker = diagnostics.get("reranker", {})
    source_diversity = diagnostics.get("source_diversity", {})

    return {
        "retrieval_recall": 1.0 if retrieved_count > 0 else 0.0,
        "retrieved_count": retrieved_count,
        "candidate_count": float(diagnostics.get("candidate_count", 0.0)),
        "source_diversity_ratio": diversity,
        "average_retrieval_score": mean(scores) if scores else 0.0,
        "max_retrieval_score": max(scores) if scores else 0.0,
        "min_retrieval_score": min(scores) if scores else 0.0,
        "reranker_applied": 1.0 if reranker.get("applied") else 0.0,
        "source_diversity_enabled": 1.0 if source_diversity.get("enabled") else 0.0,
    }


def score_citation_precision(verifications: list[dict]) -> float:
    if not verifications:
        return 0.0
    supported = sum(1 for item in verifications if item.get("support_status") == "supported")
    return supported / len(verifications)


def score_claim_support_rate(claims: list[dict]) -> float:
    if not claims:
        return 0.0
    supported = sum(1 for item in claims if item.get("verification_status") == "supported")
    return supported / len(claims)


def score_report_artifact_completeness(report_json: dict | None) -> float:
    if not report_json:
        return 0.0
    expected_keys = ["summary", "claims", "evidence", "sources", "citations"]
    present = sum(1 for key in expected_keys if key in report_json)
    return present / len(expected_keys)


def verdict_from_metrics(metrics: dict[str, float]) -> str:
    if metrics["retrieval_recall"] == 0:
        return "needs_evidence"
    if metrics["citation_precision"] < 0.5 or metrics["claim_support_rate"] < 0.5:
        return "fail"
    if metrics["report_completeness"] < 0.6:
        return "incomplete"
    return "pass"


def build_retrieval_dimension(diagnostics: dict[str, Any] | None) -> dict:
    if not diagnostics:
        return {}
    return {
        "strategy": diagnostics.get("strategy"),
        "score_type": diagnostics.get("score_type"),
        "candidate_limit": diagnostics.get("candidate_limit"),
        "top_k": diagnostics.get("top_k"),
        "chunking": diagnostics.get("chunking", {}),
        "reranker": diagnostics.get("reranker", {}),
        "source_diversity": diagnostics.get("source_diversity", {}),
    }


def _nested_get(data: dict | None, path: list[str], default):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default
