import os

from knowledgegraphs2023_openhpi.settings import load_provider_environment


def test_provider_key_from_dotenv_is_exported_for_sdk(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-or-test-value\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert load_provider_environment(env_file) is True
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-test-value"


def test_shell_provider_key_is_not_overridden_by_dotenv(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-or-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-shell")

    load_provider_environment(env_file)

    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-shell"
