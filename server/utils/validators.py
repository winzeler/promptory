"""Validation utilities for prompt front-matter fields."""

from __future__ import annotations

import re
import uuid


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value, version=4)
        return True
    except (ValueError, AttributeError):
        return False


def is_valid_semver(value: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", value))


def is_valid_snake_case(value: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9_]*$", value))


VALID_TYPES = {"chat", "completion", "tts", "transcription", "image"}
VALID_ROLES = {"system", "user", "assistant"}
VALID_ENVIRONMENTS = {"development", "staging", "production"}
VALID_MODALITY_INPUTS = {"text", "audio", "image", "video", "multimodal"}
VALID_MODALITY_OUTPUTS = {"text", "audio", "image", "tts"}
VALID_TTS_PROVIDERS = {"elevenlabs", "openai", "google"}


def validate_front_matter(fm: dict) -> list[str]:
    """Validate front-matter dict. Returns list of error messages (empty = valid)."""
    errors = []

    if "id" in fm and fm["id"] and not is_valid_uuid(fm["id"]):
        errors.append("id must be a valid UUID v4")

    if "name" not in fm or not fm.get("name"):
        errors.append("name is required")
    elif not is_valid_snake_case(fm["name"]):
        errors.append("name must be lowercase snake_case (e.g., meditation_script_relax)")

    if "version" in fm and fm["version"] and not is_valid_semver(fm["version"]):
        errors.append("version must follow semver (e.g., 1.0.0)")

    if "type" in fm and fm["type"] not in VALID_TYPES:
        errors.append(f"type must be one of: {', '.join(VALID_TYPES)}")

    if "role" in fm and fm["role"] not in VALID_ROLES:
        errors.append(f"role must be one of: {', '.join(VALID_ROLES)}")

    if "environment" in fm and fm["environment"] not in VALID_ENVIRONMENTS:
        errors.append(f"environment must be one of: {', '.join(VALID_ENVIRONMENTS)}")

    model = fm.get("model", {})
    if isinstance(model, dict):
        temp = model.get("temperature")
        if temp is not None and not (0 <= temp <= 2):
            errors.append("temperature must be between 0 and 2")
        max_tokens = model.get("max_tokens")
        if max_tokens is not None and max_tokens < 1:
            errors.append("max_tokens must be a positive integer")

    modality = fm.get("modality", {})
    if isinstance(modality, dict):
        if modality.get("input") and modality["input"] not in VALID_MODALITY_INPUTS:
            errors.append(f"modality.input must be one of: {', '.join(VALID_MODALITY_INPUTS)}")
        if modality.get("output") and modality["output"] not in VALID_MODALITY_OUTPUTS:
            errors.append(f"modality.output must be one of: {', '.join(VALID_MODALITY_OUTPUTS)}")

    tts = fm.get("tts")
    if isinstance(tts, dict):
        errors.extend(_validate_tts_config(tts))

    audio = fm.get("audio")
    if isinstance(audio, dict):
        errors.extend(_validate_audio_config(audio))

    return errors


def _validate_tts_config(tts: dict) -> list[str]:
    """Validate TTS config dict. Returns list of error messages."""
    errors = []
    provider = tts.get("provider")
    if provider is not None and provider not in VALID_TTS_PROVIDERS:
        errors.append(f"tts.provider must be one of: {', '.join(sorted(VALID_TTS_PROVIDERS))}")
    for field in ("stability", "similarity_boost", "style"):
        val = tts.get(field)
        if val is not None:
            if not isinstance(val, (int, float)) or val < 0 or val > 1:
                errors.append(f"tts.{field} must be a number between 0 and 1")
    boost = tts.get("use_speaker_boost")
    if boost is not None and not isinstance(boost, bool):
        errors.append("tts.use_speaker_boost must be a boolean")
    return errors


def _validate_audio_config(audio: dict) -> list[str]:
    """Validate audio config dict. Returns list of error messages."""
    errors = []
    duration = audio.get("target_duration_minutes")
    if duration is not None:
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append("audio.target_duration_minutes must be a positive number")
    freq = audio.get("binaural_frequency_hz")
    if freq is not None:
        if not isinstance(freq, (int, float)) or freq < 0 or freq > 40:
            errors.append("audio.binaural_frequency_hz must be between 0 and 40")
    bpm = audio.get("bpm")
    if bpm is not None:
        if not isinstance(bpm, int) or bpm <= 0:
            errors.append("audio.bpm must be a positive integer")
    return errors
