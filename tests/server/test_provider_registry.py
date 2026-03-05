"""Tests for the provider registry."""

from server.services.provider_registry import (
    get_provider_for_model,
    get_promptfoo_provider,
    get_all_known_models,
    get_registry_public,
    PROVIDERS,
)


class TestGetProviderForModel:
    def test_google_models(self):
        assert get_provider_for_model("gemini-2.0-flash") == "google"
        assert get_provider_for_model("gemini-1.5-pro") == "google"
        assert get_provider_for_model("google-custom") == "google"

    def test_openai_models(self):
        assert get_provider_for_model("gpt-4o") == "openai"
        assert get_provider_for_model("gpt-4o-mini") == "openai"
        assert get_provider_for_model("o1") == "openai"
        assert get_provider_for_model("o3-mini") == "openai"

    def test_anthropic_models(self):
        assert get_provider_for_model("claude-sonnet-4-5-20250929") == "anthropic"
        assert get_provider_for_model("claude-opus-4-6") == "anthropic"
        assert get_provider_for_model("anthropic-custom") == "anthropic"

    def test_unknown_model_returns_none(self):
        assert get_provider_for_model("custom-model-v1") is None
        assert get_provider_for_model("llama-3") is None

    def test_case_insensitive(self):
        assert get_provider_for_model("GPT-4o") == "openai"
        assert get_provider_for_model("Gemini-Pro") == "google"
        assert get_provider_for_model("Claude-3-haiku") == "anthropic"


class TestGetPromptfooProvider:
    def test_google_prefix(self):
        assert get_promptfoo_provider("gemini-2.0-flash") == "google:gemini-2.0-flash"

    def test_openai_prefix(self):
        assert get_promptfoo_provider("gpt-4o") == "openai:gpt-4o"

    def test_anthropic_prefix(self):
        assert get_promptfoo_provider("claude-sonnet-4-5-20250929") == "anthropic:claude-sonnet-4-5-20250929"

    def test_unknown_passthrough(self):
        assert get_promptfoo_provider("custom-model-v1") == "custom-model-v1"


class TestRegistryStructure:
    def test_all_providers_have_required_keys(self):
        for name, info in PROVIDERS.items():
            assert "category" in info, f"{name} missing category"
            assert "secret_keys" in info, f"{name} missing secret_keys"
            assert "models" in info, f"{name} missing models"
            assert isinstance(info["models"], list), f"{name} models should be list"

    def test_get_all_known_models(self):
        models = get_all_known_models()
        assert len(models) > 0
        assert "gpt-4o" in models
        assert "gemini-2.0-flash" in models

    def test_get_registry_public_no_secret_keys(self):
        public = get_registry_public()
        for name, info in public.items():
            assert "secret_keys" not in info
            assert "category" in info
            assert "models" in info
