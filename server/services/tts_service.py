"""TTS synthesis service — ElevenLabs integration with file-based caching."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import httpx

from server.config import settings

logger = logging.getLogger(__name__)


class TTSError(Exception):
    """Base TTS error."""


class TTSNotConfiguredError(TTSError):
    """Raised when no ElevenLabs API key is configured."""


# In-memory cache index: hash -> (file_path, created_at)
_tts_cache: dict[str, tuple[str, float]] = {}


def is_tts_configured() -> bool:
    """Check if TTS is configured (API key present)."""
    return bool(settings.elevenlabs_api_key)


def _cache_key(text: str, tts_config: dict) -> str:
    """Generate a deterministic cache key from text + config."""
    payload = f"{text}|{sorted(tts_config.items())}"
    return hashlib.sha256(payload.encode()).hexdigest()


def get_cached_audio(text: str, tts_config: dict) -> str | None:
    """Return path to cached .mp3 if it exists and is fresh."""
    key = _cache_key(text, tts_config)
    entry = _tts_cache.get(key)
    if not entry:
        return None
    file_path, created_at = entry
    ttl_seconds = settings.tts_cache_ttl_hours * 3600
    if time.time() - created_at > ttl_seconds:
        _tts_cache.pop(key, None)
        return None
    if not Path(file_path).exists():
        _tts_cache.pop(key, None)
        return None
    return file_path


def _cleanup_cache() -> None:
    """Evict oldest entries when over max."""
    if len(_tts_cache) <= settings.tts_cache_max_entries:
        return
    sorted_entries = sorted(_tts_cache.items(), key=lambda x: x[1][1])
    to_remove = len(_tts_cache) - settings.tts_cache_max_entries
    for key, (file_path, _) in sorted_entries[:to_remove]:
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            pass
        _tts_cache.pop(key, None)


async def synthesize_tts(rendered_body: str, tts_config: dict) -> str:
    """Synthesize text to speech via ElevenLabs. Returns path to .mp3 file.

    Raises:
        TTSNotConfiguredError: If no API key is set.
        TTSError: If the API call fails.
    """
    if not is_tts_configured():
        raise TTSNotConfiguredError("ElevenLabs API key not configured")

    # Check cache first
    cached = get_cached_audio(rendered_body, tts_config)
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

    # Write to cache directory
    cache_dir = Path(settings.tts_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    key = _cache_key(rendered_body, tts_config)
    file_path = str(cache_dir / f"{key}.mp3")
    Path(file_path).write_bytes(resp.content)

    _tts_cache[key] = (file_path, time.time())
    _cleanup_cache()

    logger.info("TTS synthesized and cached: %s", key[:12])
    return file_path
