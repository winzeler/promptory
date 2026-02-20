"""TTS synthesis service — ElevenLabs integration with pluggable storage."""

from __future__ import annotations

import hashlib
import logging
import time

import httpx

from server.config import settings
from server.services.tts_storage import get_tts_storage

logger = logging.getLogger(__name__)


class TTSError(Exception):
    """Base TTS error."""


class TTSNotConfiguredError(TTSError):
    """Raised when no ElevenLabs API key is configured."""


# In-memory cache index: hash -> (created_at,) for TTL tracking.
# On Lambda, this resets each cold start — acceptable since the storage
# backend (S3) is the durable layer and TTL is enforced by lifecycle rules.
_tts_cache: dict[str, float] = {}

# Pluggable storage backend (LocalTTSStorage or S3TTSStorage)
_storage = get_tts_storage()


def is_tts_configured() -> bool:
    """Check if TTS is configured (API key present)."""
    return bool(settings.elevenlabs_api_key)


def _cache_key(text: str, tts_config: dict) -> str:
    """Generate a deterministic cache key from text + config."""
    payload = f"{text}|{sorted(tts_config.items())}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def get_cached_audio(text: str, tts_config: dict) -> str | None:
    """Return a URL/path to cached audio if it exists and is fresh."""
    key = _cache_key(text, tts_config)

    # Check in-memory TTL index first (avoids storage round-trip for expired items)
    created_at = _tts_cache.get(key)
    if created_at is not None:
        ttl_seconds = settings.tts_cache_ttl_hours * 3600
        if time.time() - created_at > ttl_seconds:
            _tts_cache.pop(key, None)
            return None
    # Check storage backend
    url = await _storage.get_url(key)
    if url and key not in _tts_cache:
        # Re-populate index for warm invocations
        _tts_cache[key] = time.time()
    return url


async def synthesize_tts(rendered_body: str, tts_config: dict) -> str:
    """Synthesize text to speech via ElevenLabs. Returns URL/path to audio.

    Raises:
        TTSNotConfiguredError: If no API key is set.
        TTSError: If the API call fails.
    """
    if not is_tts_configured():
        raise TTSNotConfiguredError("ElevenLabs API key not configured")

    # Check cache first
    cached = await get_cached_audio(rendered_body, tts_config)
    if cached:
        logger.info("TTS cache hit")
        return cached

    voice_id = tts_config.get("voice_id") or settings.elevenlabs_default_voice_id
    if not voice_id:
        raise TTSError("No voice_id provided in TTS config or server defaults")

    model_id = tts_config.get("model_id") or settings.elevenlabs_default_model

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload: dict = {
        "text": rendered_body,
        "model_id": model_id,
        "voice_settings": {
            "stability": tts_config.get("stability", 0.5),
            "similarity_boost": tts_config.get("similarity_boost", 0.75),
            "style": tts_config.get("style", 0.0),
            "use_speaker_boost": tts_config.get("use_speaker_boost", True),
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("ElevenLabs API error: %s %s", e.response.status_code, e.response.text[:200])
            raise TTSError(f"ElevenLabs API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("ElevenLabs request failed: %s", e)
            raise TTSError(f"ElevenLabs request failed: {e}") from e

    # Store via the pluggable storage backend
    key = _cache_key(rendered_body, tts_config)
    await _storage.put(key, resp.content)
    _tts_cache[key] = time.time()

    # Evict oldest in-memory index entries when over max
    if len(_tts_cache) > settings.tts_cache_max_entries:
        sorted_keys = sorted(_tts_cache.items(), key=lambda x: x[1])
        to_remove = len(_tts_cache) - settings.tts_cache_max_entries
        for k, _ in sorted_keys[:to_remove]:
            _tts_cache.pop(k, None)

    logger.info("TTS synthesized and cached: %s", key[:12])

    # Return the URL/path to serve
    result = await _storage.get_url(key)
    if result is None:
        raise TTSError("Failed to retrieve stored audio after synthesis")
    return result
