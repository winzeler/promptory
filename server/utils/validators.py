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

    return errors
