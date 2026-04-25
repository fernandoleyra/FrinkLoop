import os

from core.llm import load_llm_config, validate_llm_env


def test_load_llm_config_for_openrouter(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)

    config = load_llm_config()
    assert config.provider == "openrouter"
    assert config.api_key == "test-key"
    assert config.model == "anthropic/claude-3.5-sonnet"


def test_load_llm_config_for_ollama(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("MODEL_TIMEOUT_SECONDS", raising=False)

    config = load_llm_config()
    assert config.provider == "ollama"
    assert config.base_url == "http://localhost:11434"
    assert config.model == "llama3.1"
    assert config.timeout_seconds == 180


def test_validate_llm_env_requires_matching_key(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    issues = validate_llm_env()
    assert issues == ["GROQ_API_KEY is not set"]
