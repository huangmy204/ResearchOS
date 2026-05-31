from __future__ import annotations

import time

from fastapi.testclient import TestClient

from researchos.api.main import create_app
from researchos.config import Settings
from researchos.llm import LLMResponse
from researchos.models_router import ModelProfile
from researchos.planning import LLMResearchPlanner
from researchos.reporting import LLMReportWriter
from researchos.verification import LLMCitationVerifier


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
        assert "Citation:" in report.text


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


def test_model_profiles_api_returns_role_configuration(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            basic_model="fast-model",
            reasoning_model="reasoning-model",
            writer_model="writer-model",
            verifier_model="verifier-model",
        )
    )

    with TestClient(app) as client:
        response = client.get("/v1/models")

    assert response.status_code == 200
    profiles = {profile["role"]: profile for profile in response.json()["profiles"]}
    assert profiles["searcher"]["model"] == "fast-model"
    assert profiles["planner"]["model"] == "reasoning-model"
    assert profiles["writer"]["model"] == "writer-model"
    assert profiles["verifier"]["model"] == "verifier-model"


def test_model_dry_run_api_calls_mock_llm_client(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            writer_model="writer-model",
            writer_base_url="https://api.openai.com/v1",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/models/dry-run",
            json={"role": "writer", "prompt": "Write a short report."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["role"] == "writer"
    assert body["profile"]["model"] == "writer-model"
    assert body["profile"]["provider"] == "openai"
    assert body["response"]["dry_run"] is True
    assert body["response"]["content"].startswith("[mock:writer]")
    assert body["response"]["total_tokens"] > 0


def test_model_complete_api_uses_configured_llm_client(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            writer_model="writer-model",
            writer_base_url="https://api.openai.com/v1",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/models/complete",
            json={
                "role": "writer",
                "prompt": "Write a short report.",
                "temperature": 0.1,
                "max_tokens": 64,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["role"] == "writer"
    assert body["response"]["dry_run"] is True
    assert body["response"]["content"].startswith("[mock:writer]")


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
        report_json = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.json"},
        ).json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()
        plan = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "plans/research_plan.json"},
        ).json()
        workflow_trace = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "traces/workflow_trace.json"},
        ).json()
        trace_response = client.get(f"/v1/research-runs/{run_id}/trace")

        assert sources[0]["title"] == "Legal AI memo"
        assert sources[0]["source_type"] == "file"
        assert "hallucinated citations" in evidence[0]["text"]
        assert retrieval_results[0]["score"] > 0
        assert report_json["sources"][0]["title"] == "Legal AI memo"
        assert report_json["evidence"][0]["evidence_id"] == evidence[0]["evidence_id"]
        assert eval_result["metrics"]["retrieved_count"] == 1.0
        assert eval_result["dimensions"]["retrieval"]["strategy"] == "keyword"
        assert plan[0]["agent"] == "planner"
        assert [node["node"] for node in workflow_trace["nodes"]] == [
            "planning",
            "retrieval",
            "reading",
            "evidence_extraction",
            "verification",
            "report_writing",
            "evaluation",
            "completion",
        ]
        assert workflow_trace["nodes"][0]["artifacts"] == ["plans/research_plan.json"]
        assert trace_response.status_code == 200
        trace_body = trace_response.json()
        assert trace_body["run_id"] == run_id
        assert trace_body["summary"]["node_count"] == 8
        assert trace_body["summary"]["completed"] is True
        assert trace_body["summary"]["node_names"][0] == "planning"
        assert trace_body["nodes"][5]["node"] == "report_writing"


def test_research_run_can_load_documents_from_local_corpus(tmp_path):
    workspace_root = tmp_path / "workspace"
    corpus_root = workspace_root / "corpus"
    corpus_root.mkdir(parents=True)
    (corpus_root / "legal.md").write_text(
        "# Legal Citation Memo\n\nUnsupported citations create legal research risk.",
        encoding="utf-8",
    )
    app = create_app(
        Settings(
            env="test",
            workspace_root=workspace_root,
            corpus_root=corpus_root,
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
                "query": "legal citation risk",
                "options": {"include_corpus": True},
            },
        )
        run_id = response.json()["run_id"]
        run = _wait_for_run_completion(client, run_id)
        manifest = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "inputs/corpus_manifest.json"},
        ).json()
        sources = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evidence/sources.json"},
        ).json()
        events = client.get(f"/v1/research-runs/{run_id}/events/history").json()["events"]

    assert run["status"] == "completed"
    assert run["documents"][0]["title"] == "Legal Citation Memo"
    assert run["documents"][0]["url"] == "corpus://legal.md"
    assert manifest["document_count"] == 1
    assert manifest["files"][0]["path"] == "legal.md"
    assert sources[0]["title"] == "Legal Citation Memo"
    assert "corpus.loaded" in [event["event_type"] for event in events]


def test_corpus_api_lists_available_local_corpus_files(tmp_path):
    workspace_root = tmp_path / "workspace"
    corpus_root = workspace_root / "corpus"
    corpus_root.mkdir(parents=True)
    (corpus_root / "legal.md").write_text(
        "# Legal Citation Memo\n\nUnsupported citations create legal research risk.",
        encoding="utf-8",
    )
    (corpus_root / "finance.txt").write_text(
        "Revenue recognition evidence memo.",
        encoding="utf-8",
    )
    app = create_app(
        Settings(
            env="test",
            workspace_root=workspace_root,
            corpus_root=corpus_root,
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
        )
    )

    with TestClient(app) as client:
        response = client.get("/v1/corpus")

    assert response.status_code == 200
    body = response.json()
    assert body["corpus_root"] == str(corpus_root)
    assert [file["path"] for file in body["files"]] == ["finance.txt", "legal.md"]
    assert body["files"][1]["title"] == "Legal Citation Memo"
    assert body["files"][1]["suffix"] == ".md"


def test_research_run_builds_top_k_evidence_bundle(tmp_path):
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
                        "title": "Citation risk memo",
                        "text": (
                            "Legal research citation risk increases when sources are unchecked."
                        ),
                    },
                    {
                        "title": "Agent research memo",
                        "text": (
                            "AI agents can support legal research by collecting citation evidence."
                        ),
                    },
                    {
                        "title": "Verification memo",
                        "text": (
                            "Citation verification reduces legal research risk "
                            "in generated reports."
                        ),
                    },
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        bundle = client.get(f"/v1/research-runs/{run_id}/evidence").json()
        retrieval_results = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/parsed/retrieval_results.json"},
        ).json()
        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        report = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.md"},
        )
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    assert len(retrieval_results) == 3
    assert [result["rank"] for result in retrieval_results] == [1, 2, 3]
    assert diagnostics["strategy"] == "keyword"
    assert diagnostics["score_type"] == "term_overlap"
    assert diagnostics["chunking"]["max_chunk_chars"] == 600
    assert diagnostics["retrieved_count"] == 3
    assert diagnostics["results"][0]["rank"] == 1
    assert eval_result["metrics"]["retrieved_count"] == 3.0
    assert eval_result["metrics"]["source_diversity_ratio"] == 1.0
    assert eval_result["metrics"]["average_retrieval_score"] > 0
    assert len(bundle["sources"]) == 3
    assert len(bundle["evidence"]) == 3
    assert len(bundle["claims"]) == 3
    assert len(bundle["citation_verification"]) == 3
    assert len(bundle["evidence_graph"]["nodes"]) == 9
    assert len(bundle["evidence_graph"]["edges"]) == 6
    assert "### Evidence 1" in report.text
    assert "### Evidence 3" in report.text


def test_research_run_can_use_langgraph_workflow_engine(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            workflow_engine="langgraph",
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
                        "text": "Unsupported citations create legal research risk.",
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        run = _wait_for_run_completion(client, run_id)
        trace = client.get(f"/v1/research-runs/{run_id}/trace").json()

    assert app.state.services.settings.workflow_engine == "langgraph"
    assert app.state.services.workflow.engine.__class__.__name__ == "LangGraphWorkflowEngine"
    assert run["status"] == "completed"
    assert trace["summary"]["completed"] is True
    assert trace["summary"]["node_names"] == [
        "planning",
        "retrieval",
        "reading",
        "evidence_extraction",
        "verification",
        "report_writing",
        "evaluation",
        "completion",
    ]


def test_langgraph_workflow_branches_when_retrieval_has_no_evidence(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            workflow_engine="langgraph",
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={"session_id": "session", "query": "unavailable private market memo"},
        )
        run_id = response.json()["run_id"]
        run = _wait_for_run_completion(client, run_id)
        trace = client.get(f"/v1/research-runs/{run_id}/trace").json()
        query_rewrite = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "plans/query_rewrite.json"},
        ).json()
        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        report_json = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.json"},
        ).json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    assert run["status"] == "completed"
    assert trace["summary"]["node_names"] == [
        "planning",
        "retrieval",
        "query_rewrite",
        "retrieval",
        "insufficient_evidence_report",
        "evaluation",
        "completion",
    ]
    assert query_rewrite["rewrites"][0]["failed_query"] == "unavailable private market memo"
    assert diagnostics["retry_count"] == 1
    assert diagnostics["quality_gate"]["passed"] is False
    assert diagnostics["quality_gate"]["retrieved_count"] == 0
    assert report_json["generation"]["mode"] == "insufficient_evidence"
    assert report_json["claims"] == []
    assert eval_result["verdict"] == "needs_evidence"
    assert eval_result["metrics"]["retrieval_recall"] == 0.0
    assert eval_result["metrics"]["retrieved_count"] == 0.0


def test_langgraph_workflow_branches_when_retrieval_quality_gate_fails(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            workflow_engine="langgraph",
            retrieval_min_evidence_count=2,
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": "Unsupported citations create legal research risk.",
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        run = _wait_for_run_completion(client, run_id)
        trace = client.get(f"/v1/research-runs/{run_id}/trace").json()
        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        query_rewrite = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "plans/query_rewrite.json"},
        ).json()
        report_json = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.json"},
        ).json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    assert run["status"] == "completed"
    assert trace["summary"]["node_names"] == [
        "planning",
        "retrieval",
        "query_rewrite",
        "retrieval",
        "insufficient_evidence_report",
        "evaluation",
        "completion",
    ]
    assert query_rewrite["rewrites"][0]["failed_query"] == "legal citation risk"
    assert diagnostics["retry_count"] == 1
    assert diagnostics["query_rewrites"][0]["attempt"] == 1
    assert diagnostics["quality_gate"]["passed"] is False
    assert diagnostics["quality_gate"]["min_evidence_count"] == 2
    assert diagnostics["quality_gate"]["retrieved_count"] == 1
    assert report_json["generation"]["mode"] == "insufficient_evidence"
    assert report_json["retrieval_quality"]["reason"] == "retrieved_count_below_minimum:1<2"
    assert eval_result["metrics"]["retrieval_quality_gate_passed"] == 0.0
    assert eval_result["dimensions"]["retrieval"]["retry_count"] == 1


def test_langgraph_workflow_rewrites_query_after_failed_retrieval(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            workflow_engine="langgraph",
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "case law hallucination",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": (
                            "Unsupported citations create legal research risk. "
                            "Citation verification reduces evidence risk."
                        ),
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        run = _wait_for_run_completion(client, run_id)
        trace = client.get(f"/v1/research-runs/{run_id}/trace").json()
        rewrite = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "plans/query_rewrite.json"},
        ).json()
        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    assert run["status"] == "completed"
    assert trace["summary"]["node_names"] == [
        "planning",
        "retrieval",
        "query_rewrite",
        "retrieval",
        "reading",
        "evidence_extraction",
        "verification",
        "report_writing",
        "evaluation",
        "completion",
    ]
    assert rewrite["rewrites"][0]["failed_query"] == "case law hallucination"
    assert "citation" in rewrite["rewrites"][0]["rewritten_query"]
    assert diagnostics["retry_count"] == 1
    assert diagnostics["query"] != diagnostics["original_query"]
    assert diagnostics["quality_gate"]["passed"] is True
    assert eval_result["metrics"]["retrieval_quality_gate_passed"] == 1.0
    assert eval_result["dimensions"]["retrieval"]["retry_count"] == 1


def test_research_run_can_write_report_with_llm_writer(tmp_path):
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
    app.state.services.workflow.report_writer = LLMReportWriter(
        llm_client=_StaticWorkflowLLMClient(),
        writer_profile=ModelProfile(
            role="writer",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="openai_compatible",
            configured=True,
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal research citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": "Unsupported citations create legal research risk.",
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        report = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.md"},
        )
        report_json = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "outputs/report.json"},
        ).json()

    assert "ResearchOS LLM Run Report" in report.text
    assert report_json["generation"]["mode"] == "llm"
    assert report_json["generation"]["dry_run"] is False


def test_research_run_can_verify_claim_with_llm_verifier(tmp_path):
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
    app.state.services.workflow.citation_verifier = LLMCitationVerifier(
        llm_client=_StaticVerifierLLMClient(),
        verifier_profile=ModelProfile(
            role="verifier",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="openai_compatible",
            configured=True,
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal research citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": "Unsupported citations create legal research risk.",
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        citation_verification = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evidence/citation_verification.json"},
        ).json()

    assert citation_verification[0]["verification_id"] == "ver_local_001_llm"
    assert citation_verification[0]["support_status"] == "supported"
    assert citation_verification[0]["rationale"] == "The evidence directly supports the claim."


def test_research_run_can_create_plan_with_llm_planner(tmp_path):
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
    app.state.services.workflow.research_planner = LLMResearchPlanner(
        llm_client=_StaticPlannerLLMClient(),
        planner_profile=ModelProfile(
            role="planner",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider="openai_compatible",
            configured=True,
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal research citation risk",
                "documents": [
                    {
                        "title": "Legal AI memo",
                        "text": "Unsupported citations create legal research risk.",
                    }
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        plan = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "plans/research_plan.json"},
        ).json()
        events = client.get(f"/v1/research-runs/{run_id}/events/history").json()["events"]

    assert plan[0]["goal"] == "Scope citation risk"
    assert plan[1]["agent"] == "reader"
    plan_event = next(event for event in events if event["event_type"] == "plan.created")
    assert plan_event["payload"]["steps"][0]["goal"] == "Scope citation risk"


def test_research_run_can_use_bm25_retrieval_strategy(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            retrieval_strategy="bm25",
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal citation risk",
                "documents": [
                    {
                        "title": "General AI note",
                        "text": "AI systems can support many knowledge work tasks.",
                    },
                    {
                        "title": "Citation risk memo",
                        "text": (
                            "Legal citation risk requires citation verification. "
                            "Unsupported citation references create legal research risk."
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

        assert sources[0]["title"] == "Citation risk memo"


def test_research_run_can_use_embedding_retrieval_strategy(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            retrieval_strategy="embedding",
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal citation risk",
                "documents": [
                    {
                        "title": "Cooking note",
                        "text": "Bread fermentation uses flour water salt.",
                    },
                    {
                        "title": "Citation risk memo",
                        "text": (
                            "Legal citation risk requires citation verification. "
                            "Unsupported citation evidence creates legal risk."
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
        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()

    assert app.state.services.settings.retrieval_strategy == "embedding"
    assert app.state.services.workflow.retriever.__class__.__name__ == "EmbeddingRetriever"
    assert sources[0]["title"] == "Citation risk memo"
    assert diagnostics["strategy"] == "embedding"
    assert diagnostics["score_type"] == "cosine_similarity"
    assert diagnostics["results"][0]["title"] == "Citation risk memo"


def test_research_run_can_use_term_overlap_reranker(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            retrieval_top_k=2,
            retrieval_candidate_limit=4,
            retrieval_reranker="term_overlap",
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal citation risk",
                "documents": [
                    {
                        "title": "Citation risk memo",
                        "text": "Legal citation risk requires citation verification.",
                    },
                    {
                        "title": "Legal research memo",
                        "text": "Legal research workflows need evidence tracking.",
                    },
                    {
                        "title": "Cooking note",
                        "text": "Bread fermentation uses flour water salt.",
                    },
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        bundle = client.get(f"/v1/research-runs/{run_id}/evidence").json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    assert app.state.services.workflow.reranker.__class__.__name__ == "TermOverlapReranker"
    assert diagnostics["top_k"] == 2
    assert diagnostics["candidate_limit"] == 4
    assert diagnostics["query_planner"] == "rule_based_multi_query"
    assert len(diagnostics["query_variants"]) >= 3
    assert diagnostics["query_results"][0]["kind"] == "active"
    assert diagnostics["reranker"]["name"] == "term_overlap"
    assert diagnostics["reranker"]["applied"] is True
    assert diagnostics["retrieved_count"] == 2
    assert eval_result["metrics"]["reranker_applied"] == 1.0
    assert eval_result["dimensions"]["retrieval"]["query_variant_count"] >= 3
    assert len(bundle["evidence"]) == 2


def test_research_run_can_enforce_source_diversity(tmp_path):
    app = create_app(
        Settings(
            env="test",
            workspace_root=tmp_path / "workspace",
            runtime_profile="test",
            log_level="INFO",
            api_host="127.0.0.1",
            api_port=8000,
            cors_allow_origins=[],
            retrieval_top_k=3,
            retrieval_candidate_limit=6,
            retrieval_max_chunks_per_source=1,
            retrieval_chunk_chars=55,
        )
    )
    app.state.services.workflow.step_delay_sec = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/research-runs",
            json={
                "session_id": "session",
                "query": "legal citation risk",
                "documents": [
                    {
                        "title": "Dense legal memo",
                        "text": (
                            "Legal citation risk appears in generated reports. "
                            "Legal citation risk also appears in research memos. "
                            "Legal citation risk needs verification."
                        ),
                    },
                    {
                        "title": "Verification memo",
                        "text": "Citation verification reduces legal risk.",
                    },
                    {
                        "title": "Cooking note",
                        "text": "Bread fermentation uses flour water salt.",
                    },
                ],
            },
        )
        run_id = response.json()["run_id"]
        _wait_for_run_completion(client, run_id)

        diagnostics = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/retrieval_diagnostics.json"},
        ).json()
        retrieval_results = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "sources/parsed/retrieval_results.json"},
        ).json()
        eval_result = client.get(
            f"/v1/research-runs/{run_id}/artifacts/content",
            params={"path": "evals/eval_result.json"},
        ).json()

    document_indexes = [result["document_index"] for result in retrieval_results]
    assert diagnostics["source_diversity"]["enabled"] is True
    assert diagnostics["source_diversity"]["max_chunks_per_source"] == 1
    assert diagnostics["source_diversity"]["selected_source_count"] == len(
        set(document_indexes)
    )
    assert len(document_indexes) == len(set(document_indexes))
    assert eval_result["metrics"]["source_diversity_enabled"] == 1.0
    assert eval_result["metrics"]["source_diversity_ratio"] == 1.0


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


class _StaticWorkflowLLMClient:
    def complete(self, request):
        return LLMResponse(
            content=(
                "# ResearchOS LLM Run Report\n\n"
                "## Summary\n\n"
                "The selected evidence supports the report.\n\n"
                "## Evidence\n\n"
                "Citation: `src_doc_001:ev_local_001`\n\n"
                "## Claim Verification\n\n"
                "The claim is supported.\n\n"
                "## Limitations\n\n"
                "Only one local evidence chunk was used."
            ),
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            dry_run=False,
        )


class _StaticVerifierLLMClient:
    def complete(self, request):
        return LLMResponse(
            content=(
                '{"support_status":"supported",'
                '"rationale":"The evidence directly supports the claim.",'
                '"confidence":0.93}'
            ),
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=10,
            completion_tokens=12,
            total_tokens=22,
            dry_run=False,
        )


class _StaticPlannerLLMClient:
    def complete(self, request):
        return LLMResponse(
            content=(
                '{"steps":['
                '{"step_id":"step_001","goal":"Scope citation risk","agent":"planner",'
                '"expected_output":"focused plan"},'
                '{"step_id":"step_002","goal":"Read retrieved evidence","agent":"reader",'
                '"expected_output":"evidence notes"}'
                "]} "
            ),
            model=request.profile.model,
            provider=request.profile.provider,
            prompt_tokens=15,
            completion_tokens=25,
            total_tokens=40,
            dry_run=False,
        )
