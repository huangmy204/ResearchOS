from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from pydantic import BaseModel, Field

from researchos.api.services import build_services
from researchos.config import get_settings
from researchos.models.run import ResearchDocument, ResearchRunCreate


class EvalCase(BaseModel):
    case_id: str
    query: str = Field(min_length=1)
    documents: list[ResearchDocument] = Field(default_factory=list)
    expected_source_keywords: list[str] = Field(default_factory=list)
    expected_report_sections: list[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    eval_run_id: str
    case_id: str
    research_run_id: str
    metrics: dict[str, float]
    verdict: str
    regression: bool = False


async def run_dataset(dataset_path: Path) -> list[EvalResult]:
    settings = get_settings()
    services = build_services(settings)
    services.workflow.step_delay_sec = 0

    cases = load_cases(dataset_path)
    results: list[EvalResult] = []
    for case in cases:
        results.append(await run_case(case, services))
    write_dataset_report(dataset_path, results)
    return results


def load_cases(dataset_path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(EvalCase.model_validate(json.loads(line)))
    return cases


async def run_case(case: EvalCase, services) -> EvalResult:
    request = ResearchRunCreate(
        session_id=f"eval_{case.case_id}",
        request_id=f"eval_{case.case_id}",
        query=case.query,
        documents=case.documents,
        options={"enable_eval": True},
    )
    run = services.run_store.create(request)
    services.event_store.append(run, "run.created", {"run_id": run.run_id, "query": run.query})
    await services.workflow.run(run.run_id)

    completed = services.run_store.get(run.run_id)
    if completed is None:
        raise RuntimeError(f"Run disappeared during eval: {run.run_id}")

    report_text, _ = services.artifact_store.read_text(completed, "outputs/report.md")
    sources = services.artifact_store.read_json(completed, "evidence/sources.json")
    claims = services.artifact_store.read_json(completed, "evidence/claims.json")
    citation_verification = services.artifact_store.read_json(
        completed, "evidence/citation_verification.json"
    )

    metrics = {
        "retrieval_recall": score_keyword_recall(case.expected_source_keywords, sources),
        "citation_precision": score_citation_precision(citation_verification),
        "claim_support_rate": score_claim_support_rate(claims),
        "report_completeness": score_report_completeness(
            case.expected_report_sections, report_text
        ),
        "latency_sec": 0.0,
        "estimated_cost": 0.0,
        "tool_success_rate": 1.0 if completed.status == "completed" else 0.0,
    }
    verdict = "pass" if min_quality_score(metrics) >= 0.5 else "fail"
    result = EvalResult(
        eval_run_id=f"eval_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{case.case_id}",
        case_id=case.case_id,
        research_run_id=completed.run_id,
        metrics=metrics,
        verdict=verdict,
    )
    services.artifact_store.write_json(completed, "evals/eval_result.json", result.model_dump())
    services.artifact_store.write_text(completed, "evals/eval_report.md", build_eval_report(result))
    return result


def score_keyword_recall(expected_keywords: list[str], sources: object) -> float:
    if not expected_keywords:
        return 1.0
    haystack = json.dumps(sources, ensure_ascii=False).lower()
    matched = sum(1 for keyword in expected_keywords if keyword.lower() in haystack)
    return matched / len(expected_keywords)


def score_citation_precision(citation_verification: object) -> float:
    items = citation_verification if isinstance(citation_verification, list) else []
    if not items:
        return 0.0
    supported = sum(1 for item in items if item.get("support_status") == "supported")
    return supported / len(items)


def score_claim_support_rate(claims: object) -> float:
    items = claims if isinstance(claims, list) else []
    if not items:
        return 0.0
    supported = sum(1 for item in items if item.get("verification_status") == "supported")
    return supported / len(items)


def score_report_completeness(expected_sections: list[str], report_text: str) -> float:
    if not expected_sections:
        return 1.0
    report_lower = report_text.lower()
    matched = sum(1 for section in expected_sections if section.lower() in report_lower)
    return matched / len(expected_sections)


def min_quality_score(metrics: dict[str, float]) -> float:
    quality_metrics = [
        metrics["retrieval_recall"],
        metrics["citation_precision"],
        metrics["claim_support_rate"],
        metrics["report_completeness"],
        metrics["tool_success_rate"],
    ]
    return min(quality_metrics)


def write_dataset_report(dataset_path: Path, results: list[EvalResult]) -> None:
    reports_dir = Path("evals/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{dataset_path.stem}_latest.json"
    summary = {
        "dataset": str(dataset_path),
        "case_count": len(results),
        "pass_count": sum(1 for result in results if result.verdict == "pass"),
        "avg_metrics": average_metrics(results),
        "results": [result.model_dump() for result in results],
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def average_metrics(results: list[EvalResult]) -> dict[str, float]:
    if not results:
        return {}
    metric_names = results[0].metrics.keys()
    return {
        metric: round(mean(result.metrics[metric] for result in results), 4)
        for metric in metric_names
    }


def build_eval_report(result: EvalResult) -> str:
    lines = [
        "# Eval Report",
        "",
        f"Case ID: `{result.case_id}`",
        f"Research Run ID: `{result.research_run_id}`",
        f"Verdict: `{result.verdict}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(f"- {name}: {value:.2f}" for name, value in result.metrics.items())
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ResearchOS eval dataset.")
    parser.add_argument("--dataset", required=True, type=Path)
    args = parser.parse_args()
    results = asyncio.run(run_dataset(args.dataset))
    print(json.dumps([result.model_dump() for result in results], indent=2))


if __name__ == "__main__":
    main()
