"""Tests for front-matter parsing, serialization, and validation."""

from __future__ import annotations

import json
import uuid

from server.utils.front_matter import (
    body_hash,
    ensure_id,
    ensure_version,
    extract_tags,
    front_matter_to_json,
    parse_prompt_file,
    serialize_prompt_file,
)
from server.utils.validators import (
    is_valid_semver,
    is_valid_snake_case,
    is_valid_uuid,
    validate_front_matter,
)


# ---------------------------------------------------------------------------
# front_matter.py tests
# ---------------------------------------------------------------------------


class TestParsePromptFile:
    def test_basic_parse(self):
        content = "---\nname: greeting\nversion: 1.0.0\n---\nHello {{ name }}!"
        fm, body = parse_prompt_file(content)
        assert fm["name"] == "greeting"
        assert fm["version"] == "1.0.0"
        assert body == "Hello {{ name }}!"

    def test_empty_front_matter(self):
        content = "---\n---\nJust a body."
        fm, body = parse_prompt_file(content)
        assert fm == {}
        assert body == "Just a body."

    def test_no_front_matter(self):
        content = "No front matter here."
        fm, body = parse_prompt_file(content)
        assert fm == {}
        assert body == "No front matter here."

    def test_complex_front_matter(self):
        content = """---
name: meditation_script
type: chat
model:
  default: gemini-2.0-flash
  temperature: 0.7
tags:
  - meditation
  - wellness
---
You are a meditation guide."""
        fm, body = parse_prompt_file(content)
        assert fm["name"] == "meditation_script"
        assert fm["model"]["default"] == "gemini-2.0-flash"
        assert fm["model"]["temperature"] == 0.7
        assert "meditation" in fm["tags"]
        assert body == "You are a meditation guide."


class TestSerializePromptFile:
    def test_roundtrip(self):
        fm = {"name": "test_prompt", "version": "1.0.0"}
        body = "Hello {{ name }}!"
        serialized = serialize_prompt_file(fm, body)
        fm2, body2 = parse_prompt_file(serialized)
        assert fm2["name"] == "test_prompt"
        assert fm2["version"] == "1.0.0"
        assert body2 == "Hello {{ name }}!"


class TestBodyHash:
    def test_deterministic(self):
        h1 = body_hash("Hello world")
        h2 = body_hash("Hello world")
        assert h1 == h2

    def test_different_inputs(self):
        h1 = body_hash("Hello")
        h2 = body_hash("World")
        assert h1 != h2

    def test_length(self):
        h = body_hash("test")
        assert len(h) == 16


class TestEnsureId:
    def test_adds_id_when_missing(self):
        fm = {"name": "test"}
        result = ensure_id(fm)
        assert "id" in result
        assert is_valid_uuid(result["id"])

    def test_preserves_existing_id(self):
        existing = str(uuid.uuid4())
        fm = {"id": existing, "name": "test"}
        result = ensure_id(fm)
        assert result["id"] == existing

    def test_replaces_empty_id(self):
        fm = {"id": "", "name": "test"}
        result = ensure_id(fm)
        assert result["id"] != ""
        assert is_valid_uuid(result["id"])


class TestEnsureVersion:
    def test_bump_patch(self):
        fm = {"version": "1.2.3"}
        result = ensure_version(fm, "patch")
        assert result["version"] == "1.2.4"

    def test_bump_minor(self):
        fm = {"version": "1.2.3"}
        result = ensure_version(fm, "minor")
        assert result["version"] == "1.3.0"

    def test_bump_major(self):
        fm = {"version": "1.2.3"}
        result = ensure_version(fm, "major")
        assert result["version"] == "2.0.0"

    def test_missing_version(self):
        fm = {}
        result = ensure_version(fm)
        assert result["version"] == "0.0.1"

    def test_empty_version(self):
        fm = {"version": ""}
        result = ensure_version(fm)
        assert result["version"] == "0.0.1"

    def test_malformed_version(self):
        fm = {"version": "abc"}
        result = ensure_version(fm)
        assert result["version"] == "0.0.1"


class TestFrontMatterToJson:
    def test_serializes(self):
        fm = {"name": "test", "tags": ["a", "b"]}
        result = front_matter_to_json(fm)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["tags"] == ["a", "b"]


class TestExtractTags:
    def test_list_tags(self):
        result = extract_tags({"tags": ["a", "b"]})
        assert json.loads(result) == ["a", "b"]

    def test_no_tags(self):
        result = extract_tags({})
        assert json.loads(result) == []

    def test_non_list_tags(self):
        result = extract_tags({"tags": "not-a-list"})
        assert result == "[]"


# ---------------------------------------------------------------------------
# validators.py tests
# ---------------------------------------------------------------------------


class TestValidators:
    def test_valid_uuid(self):
        assert is_valid_uuid(str(uuid.uuid4()))

    def test_invalid_uuid(self):
        assert not is_valid_uuid("not-a-uuid")
        assert not is_valid_uuid("")

    def test_valid_semver(self):
        assert is_valid_semver("1.0.0")
        assert is_valid_semver("0.0.1")
        assert is_valid_semver("10.20.30")

    def test_invalid_semver(self):
        assert not is_valid_semver("1.0")
        assert not is_valid_semver("abc")
        assert not is_valid_semver("1.0.0-beta")

    def test_valid_snake_case(self):
        assert is_valid_snake_case("hello")
        assert is_valid_snake_case("hello_world")
        assert is_valid_snake_case("meditation_script_relax")

    def test_invalid_snake_case(self):
        assert not is_valid_snake_case("Hello")
        assert not is_valid_snake_case("hello-world")
        assert not is_valid_snake_case("123abc")
        assert not is_valid_snake_case("")


class TestValidateFrontMatter:
    def test_valid(self):
        fm = {
            "id": str(uuid.uuid4()),
            "name": "test_prompt",
            "version": "1.0.0",
            "type": "chat",
            "role": "system",
            "environment": "production",
        }
        errors = validate_front_matter(fm)
        assert errors == []

    def test_missing_name(self):
        errors = validate_front_matter({})
        assert any("name is required" in e for e in errors)

    def test_bad_name(self):
        errors = validate_front_matter({"name": "Not-Snake-Case"})
        assert any("snake_case" in e for e in errors)

    def test_invalid_type(self):
        errors = validate_front_matter({"name": "test", "type": "invalid"})
        assert any("type must be one of" in e for e in errors)

    def test_invalid_role(self):
        errors = validate_front_matter({"name": "test", "role": "invalid"})
        assert any("role must be one of" in e for e in errors)

    def test_invalid_environment(self):
        errors = validate_front_matter({"name": "test", "environment": "invalid"})
        assert any("environment must be one of" in e for e in errors)

    def test_temperature_out_of_range(self):
        errors = validate_front_matter({"name": "test", "model": {"temperature": 3.0}})
        assert any("temperature" in e for e in errors)

    def test_negative_max_tokens(self):
        errors = validate_front_matter({"name": "test", "model": {"max_tokens": -1}})
        assert any("max_tokens" in e for e in errors)

    def test_invalid_modality(self):
        errors = validate_front_matter({"name": "test", "modality": {"input": "smell"}})
        assert any("modality.input" in e for e in errors)

    def test_invalid_uuid_id(self):
        errors = validate_front_matter({"name": "test", "id": "not-uuid"})
        assert any("UUID" in e for e in errors)
