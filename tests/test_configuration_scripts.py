from pathlib import Path

from scripts.configure_gemini import update_env


def test_gemini_configuration_preserves_openai_key(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OPENAI_API_KEY=keep-this-secret\n"
        "LEGAL_AGENT_PROVIDER=openai\n"
        "LEGAL_AGENT_MODEL=gpt-test\n",
        encoding="utf-8",
    )

    update_env(env_path, {
        "LEGAL_AGENT_PROVIDER": "gemini",
        "GEMINI_API_KEY": "new-gemini-secret",
        "GEMINI_MODEL": "gemini-test",
    })

    configured = env_path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=keep-this-secret" in configured
    assert "LEGAL_AGENT_MODEL=gpt-test" in configured
    assert "LEGAL_AGENT_PROVIDER=gemini" in configured
    assert "GEMINI_API_KEY=new-gemini-secret" in configured
    assert "GEMINI_MODEL=gemini-test" in configured
