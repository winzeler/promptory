"""Provider registry — known providers, model mapping, and metadata."""

from __future__ import annotations

PROVIDERS: dict[str, dict] = {
    "elevenlabs": {
        "category": "tts",
        "secret_keys": ["api_key"],
        "models": [
            "eleven_multilingual_v2",
            "eleven_monolingual_v1",
            "eleven_turbo_v2",
            "eleven_turbo_v2_5",
        ],
        "config_keys": ["default_voice_id", "default_model"],
    },
    "openai": {
        "category": "llm+tts",
        "secret_keys": ["api_key"],
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "o1",
            "o1-mini",
            "o3-mini",
        ],
        "tts_models": ["tts-1", "tts-1-hd"],
        "config_keys": ["organization"],
    },
    "anthropic": {
        "category": "llm",
        "secret_keys": ["api_key"],
        "models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
        "config_keys": [],
    },
    "google": {
        "category": "llm",
        "secret_keys": ["api_key"],
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "config_keys": [],
    },
}

# Model-string patterns to provider name.
_MODEL_PATTERNS: list[tuple[list[str], str]] = [
    (["gemini", "google"], "google"),
    (["gpt", "openai", "o1", "o3"], "openai"),
    (["claude", "anthropic"], "anthropic"),
]

# Promptfoo provider prefix per provider.
PROMPTFOO_PREFIXES: dict[str, str] = {
    "google": "google",
    "openai": "openai",
    "anthropic": "anthropic",
}

# Provider → environment variable name for API key.
ENV_VAR_NAMES: dict[str, str] = {
    "elevenlabs": "ELEVENLABS_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def get_provider_for_model(model: str) -> str | None:
    """Map a model string to its provider name, or None if unknown."""
    lower = model.lower()
    for patterns, provider in _MODEL_PATTERNS:
        if any(p in lower for p in patterns):
            return provider
    return None


def get_promptfoo_provider(model: str) -> str:
    """Map a model string to a promptfoo provider string (e.g. 'openai:gpt-4o')."""
    provider = get_provider_for_model(model)
    prefix = PROMPTFOO_PREFIXES.get(provider or "")
    if prefix:
        return f"{prefix}:{model}"
    return model


def get_all_known_models() -> list[str]:
    """Return a flat list of all known model identifiers."""
    models = []
    for info in PROVIDERS.values():
        models.extend(info.get("models", []))
    return models


def get_registry_public() -> dict:
    """Return provider metadata safe for API responses (no secrets)."""
    result = {}
    for name, info in PROVIDERS.items():
        result[name] = {
            "category": info["category"],
            "models": info.get("models", []),
            "config_keys": info.get("config_keys", []),
        }
        if "tts_models" in info:
            result[name]["tts_models"] = info["tts_models"]
    return result
