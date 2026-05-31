from __future__ import annotations

from researchos.config import get_settings, load_local_env


def test_load_local_env_reads_key_value_pairs(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# local secrets",
                "RESEARCHOS_LLM_CLIENT=openai_compatible",
                "RESEARCHOS_WORKFLOW_ENGINE=langgraph",
                "WRITER_MODEL='qwen-plus'",
                'WRITER_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("RESEARCHOS_LLM_CLIENT", raising=False)
    monkeypatch.delenv("RESEARCHOS_WORKFLOW_ENGINE", raising=False)
    monkeypatch.delenv("WRITER_MODEL", raising=False)
    monkeypatch.delenv("WRITER_BASE_URL", raising=False)

    loaded = load_local_env(env_file)

    assert loaded is True
    assert get_settings().llm_client == "openai_compatible"
    assert get_settings().workflow_engine == "langgraph"
    assert get_settings().writer_model == "qwen-plus"
    assert get_settings().writer_base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_load_local_env_does_not_override_existing_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WRITER_MODEL=qwen-plus", encoding="utf-8")
    monkeypatch.setenv("WRITER_MODEL", "deepseek-chat")

    load_local_env(env_file)

    assert get_settings().writer_model == "deepseek-chat"
