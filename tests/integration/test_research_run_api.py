from __future__ import annotations

import time

from fastapi.testclient import TestClient

from researchos.api.main import create_app
from researchos.config import Settings


def test_research_run_lifecycle_creates_artifacts(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "tenant_id": "tenant",
                "user_id": "user",
                "session_id": "session",
                "query": "Analyze AI agents for legal research.",
            },
        )

        assert response.status_code == 201
        run_id = response.json()["run_id"]

        run = _wait_for_run_completion(client, run_id)
        assert run["status"] == "completed"

        artifacts = client.get(f"/v1/research-runs/{run_id}/artifacts").json()["artifacts"]
        artifact_paths = {artifact["path"] for artifact in artifacts}
        assert "outputs/report.md" in artifact_paths
        assert "evidence/evidence_graph.json" in artifact_paths

        report = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.md"},
        )
        assert report.status_code == 200
        assert "ResearchOS MVP Run Report" in report.text


def test_artifact_api_rejects_escaping_paths(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={"session_id": "session", "query": "test"},
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        escaped = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "../README"},
        )
        assert escaped.status_code == 400


def test_research_run_create_is_idempotent_with_request_id(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    payload = {
        "tenant_id": "tenant",
        "user_id": "user",
        "session_id": "session",
        "request_id": "req-001",
        "query": "Analyze AI agents for legal research.",
    }

    with TestClient(app) as client:
        first = client.post("/v1/research-runs", json=payload)
        second = client.post("/v1/research-runs", json=payload)

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["run_id"] == first.json()["run_id"]


def test_list_research_runs_and_event_history(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={"session_id": "session", "query": "list and inspect this run"},
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        runs = client.get("/v1/research-runs")
        assert runs.status_code == 200
        assert [run["run_id"] for run in runs.json()["runs"]] == [run_id]

        events = client.get(f"/v1/research-runs/{run_id}/events/history")
        assert events.status_code == 200
        event_types = [event["event_type"] for event in events.json()["events"]]
        assert "run.created" in event_types
        assert "report.completed" in event_types


def test_research_run_uses_local_documents_for_evidence(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal research citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": (
                            "AI agents can reduce legal research time by searching cases. "
                            "A key risk is hallucinated citations that are not supported "
                            "by evidence."
                        ),
                    },
                    {
                        "title": "Cooking note",
                        "text": (
                            "Sourdough bread needs flour, water, salt, and patient "
                            "fermentation."
                        ),
                    },
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        sources = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evidence/sources.json"},
        ).json()
        evidence = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evidence/evidence.json"},
        ).json()
        retrieval_results = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/parsed/retrieval_results.json"},
        ).json()

        assert sources[0]["title"] == "Legal AI memo"
        assert sources[0]["source_type"] == "file"
        assert "hallucinated citations" in evidence[0]["text"]
        assert retrieval_results[0]["score"] > 0


def test_evidence_api_returns_bundle_and_graph(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
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
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        bundle = client.get(f"/v1/research-runs/{run_id}/evidence")
        assert bundle.status_code == 200
        bundle_json = bundle.json()
        assert bundle_json["run_id"] == run_id
        assert bundle_json["sources"][0]["title"] == "Legal AI memo"
        assert bundle_json["evidence"][0]["source_id"] == bundle_json["sources"][0]["source_id"]
        assert bundle_json["claims"][0]["evidence_ids"] == [
            bundle_json["evidence"][0]["evidence_id"]
        ]
        assert bundle_json["citation_verification"][0]["support_status"] == "supported"

        graph = client.get(f"/v1/research-runs/{run_id}/evidence/graph")
        assert graph.status_code == 200
        graph_json = graph.json()
        assert graph_json["run_id"] == run_id
        assert len(graph_json["nodes"]) >= 3
        assert len(graph_json["edges"]) >= 2


def test_cancelled_research_run_does_not_complete_or_write_report(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )
    app.state.services.workflow.step_delay_sec = 0.2

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={"session_id": "session", "query": "cancel this run"},
        )
        run_id = response.json()["run_id"]

        cancelled = client.post(f"/v1/research-runs/{run_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        time.sleep(0.5)

        run = client.get(f"/v1/research-runs/{run_id}").json()
        assert run["status"] == "cancelled"

        artifacts = client.get(f"/v1/research-runs/{run_id}/artifacts").json()["artifacts"]
        artifact_paths = {artifact["path"] for artifact in artifacts}
        assert "outputs/report.md" not in artifact_paths


def _wait_for_run_completion(client: TestClient, run_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/v1/research-runs/{run_id}")
        response.raise_for_status()
        run = response.json()
        if run["status"] in {"completed", "failed", "cancelled"}:
            return run
        time.sleep(0.05)
    raise AssertionError("Run did not finish in time.")
