"""
core/llm.py — Provider abstraction for FrinkLoop model calls.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.3
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    timeout_seconds: int = 30
    base_url: str = ""
    api_key: str = ""


def load_llm_config() -> LLMConfig:
    provider = os.getenv("MODEL_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER
    model = os.getenv("MODEL_NAME", "").strip()

    if not model:
        model_defaults = {
            "anthropic": DEFAULT_MODEL,
            "openrouter": "anthropic/claude-3.5-sonnet",
            "groq": "llama-3.3-70b-versatile",
            "ollama": DEFAULT_OLLAMA_MODEL,
            "gemini": "gemini-2.0-flash",
        }
        model = model_defaults.get(provider, DEFAULT_MODEL)

    max_tokens = _env_int("MODEL_MAX_TOKENS", DEFAULT_MAX_TOKENS)
    temperature = _env_float("MODEL_TEMPERATURE", DEFAULT_TEMPERATURE)
    default_timeout = 180 if provider == "ollama" else 120
    timeout_seconds = _env_int("MODEL_TIMEOUT_SECONDS", default_timeout)

    if provider == "anthropic":
        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        )
    if provider == "openrouter":
        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
            api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        )
    if provider == "groq":
        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip(),
            api_key=os.getenv("GROQ_API_KEY", "").strip(),
        )
    if provider == "ollama":
        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip(),
        )
    if provider == "gemini":
        return LLMConfig(
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        )

    raise ValueError(f"Unsupported MODEL_PROVIDER: {provider}")


def validate_llm_env() -> list[str]:
    try:
        config = load_llm_config()
    except ValueError as exc:
        return [str(exc)]

    if config.provider in {"anthropic", "openrouter", "groq", "gemini"} and not config.api_key:
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        return [f"{env_map[config.provider]} is not set"]

    if config.provider == "ollama" and not config.base_url:
        return ["OLLAMA_BASE_URL is not set"]

    return []


def call_llm(system: str, user: str, *, max_tokens: int | None = None) -> str:
    config = load_llm_config()
    token_limit = max_tokens or config.max_tokens

    if config.provider == "anthropic":
        return _call_anthropic(config, system, user, token_limit)
    if config.provider in {"openrouter", "groq"}:
        return _call_openai_compatible(config, system, user, token_limit)
    if config.provider == "ollama":
        return _call_ollama(config, system, user)
    if config.provider == "gemini":
        return _call_gemini(config, system, user, token_limit)
    raise ValueError(f"Unsupported MODEL_PROVIDER: {config.provider}")


def is_local_provider() -> bool:
    return load_llm_config().provider == "ollama"


def call_llm_with_tools(
    system: str,
    user: str,
    tools: list[dict],
    tool_executor,
    *,
    max_tokens: int | None = None,
    max_rounds: int = 15,
) -> str:
    """
    Multi-turn tool-calling loop (Anthropic only).
    Falls back to call_llm for other providers or when tools list is empty.

    tool_executor: callable(name: str, inputs: dict) -> str
    Returns the final assistant text after all tool calls complete.
    """
    config = load_llm_config()
    if config.provider != "anthropic" or not tools:
        return call_llm(system, user, max_tokens=max_tokens)

    token_limit = max_tokens or config.max_tokens
    messages: list[dict] = [{"role": "user", "content": user}]
    last_text = ""

    for _ in range(max_rounds):
        payload = {
            "model": config.model,
            "max_tokens": token_limit,
            "temperature": config.temperature,
            "system": system,
            "tools": tools,
            "messages": messages,
        }
        data = _http_json(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload=payload,
            timeout=config.timeout_seconds,
        )

        stop_reason = data.get("stop_reason", "end_turn")
        content_blocks: list[dict] = data.get("content", [])

        text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
        if text_parts:
            last_text = "\n".join(text_parts)

        if stop_reason == "end_turn":
            return last_text

        if stop_reason != "tool_use":
            return last_text

        # Execute all tool_use blocks in this turn
        tool_results = []
        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue
            result_text = tool_executor(block["name"], block.get("input", {}))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": result_text,
            })

        messages.append({"role": "assistant", "content": content_blocks})
        messages.append({"role": "user", "content": tool_results})

    return last_text


def verify_llm_connection() -> tuple[bool, str]:
    try:
        config = load_llm_config()
        if config.provider == "anthropic":
            _http_json(
                "GET",
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": config.api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=config.timeout_seconds,
            )
            return True, "Anthropic API key verified"
        if config.provider == "openrouter":
            _http_json(
                "GET",
                f"{config.base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
                timeout=config.timeout_seconds,
            )
            return True, "OpenRouter API key verified"
        if config.provider == "groq":
            _http_json(
                "GET",
                f"{config.base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {config.api_key}"},
                timeout=config.timeout_seconds,
            )
            return True, "Groq API key verified"
        if config.provider == "ollama":
            _http_json("GET", f"{config.base_url.rstrip('/')}/api/tags", timeout=config.timeout_seconds)
            return True, f"Ollama reachable at {config.base_url}"
        if config.provider == "gemini":
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={urllib.parse.quote(config.api_key)}"
            )
            _http_json("GET", url, timeout=config.timeout_seconds)
            return True, "Gemini API key verified"
    except Exception as exc:
        return False, str(exc)

    return False, "Unknown provider"


def _call_anthropic(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    payload = {
        "model": config.model,
        "max_tokens": max_tokens,
        "temperature": config.temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    data = _http_json(
        "POST",
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload=payload,
        timeout=config.timeout_seconds,
    )
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def _call_openai_compatible(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.temperature,
        "max_tokens": max_tokens,
    }
    data = _http_json(
        "POST",
        f"{config.base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "content-type": "application/json",
        },
        payload=payload,
        timeout=config.timeout_seconds,
    )
    return data["choices"][0]["message"]["content"]


def _call_ollama(config: LLMConfig, system: str, user: str) -> str:
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
        },
    }
    data = _http_json(
        "POST",
        f"{config.base_url.rstrip('/')}/api/chat",
        headers={"content-type": "application/json"},
        payload=payload,
        timeout=config.timeout_seconds,
    )
    return data.get("message", {}).get("content", "")


def _call_gemini(config: LLMConfig, system: str, user: str, max_tokens: int) -> str:
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": config.temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(config.model)}:generateContent?key={urllib.parse.quote(config.api_key)}"
    )
    data = _http_json(
        "POST",
        url,
        headers={"content-type": "application/json"},
        payload=payload,
        timeout=config.timeout_seconds,
    )
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts)


def _http_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode()
    return json.loads(body) if body else {}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
