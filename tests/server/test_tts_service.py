"""Tests for TTS service — caching, configuration, and synthesis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from server.services.tts_service import (
    _cache_key,
    is_tts_configured,
    synthesize_tts,
    TTSNotConfiguredError,
    TTSError,
    _tts_cache,
)


class TestCacheKey:
    def test_deterministic(self):
        key1 = _cache_key("Hello world", {"provider": "elevenlabs"})
        key2 = _cache_key("Hello world", {"provider": "elevenlabs"})
        assert key1 == key2

    def test_different_body_different_key(self):
        key1 = _cache_key("Hello", {"provider": "elevenlabs"})
        key2 = _cache_key("World", {"provider": "elevenlabs"})
        assert key1 != key2

    def test_different_config_different_key(self):
        key1 = _cache_key("Hello", {"provider": "elevenlabs"})
        key2 = _cache_key("Hello", {"provider": "openai"})
        assert key1 != key2


class TestIsConfigured:
    def test_empty_key_not_configured(self):
        with patch("server.services.tts_service.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = ""
            assert is_tts_configured() is False

    def test_set_key_is_configured(self):
        with patch("server.services.tts_service.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = "sk-test-key"
            assert is_tts_configured() is True


class TestSynthesizeTTS:
    @pytest.mark.asyncio
    async def test_not_configured_raises(self):
        with patch("server.services.tts_service.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = ""
            with pytest.raises(TTSNotConfiguredError):
                await synthesize_tts("Hello", {"provider": "elevenlabs"})

    @pytest.mark.asyncio
    async def test_missing_voice_id_raises(self):
        with patch("server.services.tts_service.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = "sk-test"
            mock_settings.elevenlabs_default_voice_id = ""
            mock_settings.tts_cache_dir = "/tmp/tts_test_cache"
            mock_settings.tts_cache_ttl_hours = 24
            mock_settings.tts_cache_max_entries = 100
            # Clear cache to avoid hitting it
            _tts_cache.clear()
            with pytest.raises(TTSError, match="No voice_id"):
                await synthesize_tts("Hello", {})

    @pytest.mark.asyncio
    async def test_successful_synthesis(self, tmp_path):
        """Test successful TTS synthesis with mocked httpx."""
        _tts_cache.clear()

        mock_response = MagicMock()
        mock_response.content = b"\xff\xfb\x90\x00" * 100  # Fake MP3 bytes
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        cache_dir = str(tmp_path / "tts_cache")

        with patch("server.services.tts_service.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = "sk-test"
            mock_settings.elevenlabs_default_voice_id = ""
            mock_settings.elevenlabs_default_model = "eleven_multilingual_v2"
            mock_settings.tts_cache_dir = cache_dir
            mock_settings.tts_cache_ttl_hours = 24
            mock_settings.tts_cache_max_entries = 100

            with patch("server.services.tts_service.httpx.AsyncClient", return_value=mock_client):
                result = await synthesize_tts(
                    "Hello, this is a test.",
                    {"provider": "elevenlabs", "voice_id": "test-voice-123"},
                )

        assert result.endswith(".mp3")
        import os
        assert os.path.exists(result)
        _tts_cache.clear()
