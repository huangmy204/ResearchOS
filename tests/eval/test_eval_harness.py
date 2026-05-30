from __future__ import annotations

import json

import pytest

from researchos.evals.harness import run_dataset


@pytest.mark.anyio
async def test_eval_harness_runs_dataset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RESEARCHOS_WORKSPACE_ROOT", str(tmp_path / "workspace"))

    dataset = tmp_path / "smoke_cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "smoke_001",
                "query": "legal research citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": (
                            "Legal research assistants need citation verification. "
                            "Unsupported citations create professional risk."
                        ),
                    }
                ],
                "expected_source_keywords": ["Legal AI memo"],
                "expected_report_sections": ["Summary", "Evidence", "Claim Verification"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    results = await run_dataset(dataset)

    assert len(results) == 1
    assert results[0].verdict == "pass"
    assert results[0].metrics["retrieval_recall"] == 1.0
    assert (tmp_path / "evals" / "reports" / "smoke_cases_latest.json").is_file()
