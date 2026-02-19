"""Tests for Prompty format conversion."""

from __future__ import annotations

import pytest

from server.utils.prompty_converter import md_to_prompty, prompty_to_md


class TestMdToPrompty:
    def test_basic_conversion(self):
        fm = {
            "name": "greeting",
            "description": "A greeting prompt",
            "version": "1.0.0",
            "tags": ["greetings", "chat"],
        }
        body = "Hello {{ name }}, welcome!"
        result = md_to_prompty(fm, body)

        assert result.startswith("---\n")
        assert "name: greeting" in result
        assert "description: A greeting prompt" in result
        assert "Hello {{ name }}, welcome!" in result

    def test_model_mapping(self):
        fm = {
            "name": "model-test",
            "model": {
                "default": "gemini-2.0-flash",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        }
        result = md_to_prompty(fm, "Test body")

        assert "api: chat" in result
        assert "name: gemini-2.0-flash" in result
        assert "temperature: 0.7" in result
        assert "max_tokens: 1024" in result

    def test_tts_prompt(self):
        fm = {
            "name": "meditation-intro",
            "description": "TTS meditation",
            "version": "2.0.0",
            "org": "futureself",
        }
        body = "Take a deep breath, {{ name }}."
        result = md_to_prompty(fm, body)

        assert "authors:" in result
        assert "- futureself" in result
        assert "Take a deep breath" in result

    def test_empty_front_matter(self):
        result = md_to_prompty({}, "Just a body")
        assert "---" in result
        assert "Just a body" in result

    def test_variables_become_sample(self):
        fm = {
            "name": "test",
            "variables": {"name": "Alice", "role": "assistant"},
        }
        result = md_to_prompty(fm, "Hi {{ name }}")
        assert "sample:" in result
        assert "name: Alice" in result


class TestPromptyToMd:
    def test_basic_parse(self):
        prompty = """---
name: greeting
description: A greeting prompt
version: 1.0.0
---
Hello {{ name }}!"""

        fm, body = prompty_to_md(prompty)
        assert fm["name"] == "greeting"
        assert fm["description"] == "A greeting prompt"
        assert fm["version"] == "1.0.0"
        assert "Hello {{ name }}!" in body

    def test_model_reverse_mapping(self):
        prompty = """---
name: model-test
model:
  api: chat
  configuration:
    name: gpt-4
  parameters:
    temperature: 0.5
    max_tokens: 2048
---
Test body"""

        fm, body = prompty_to_md(prompty)
        assert fm["model"]["default"] == "gpt-4"
        assert fm["model"]["temperature"] == 0.5
        assert fm["model"]["max_tokens"] == 2048

    def test_authors_to_org(self):
        prompty = """---
name: test
authors:
  - futureself
---
Body"""

        fm, body = prompty_to_md(prompty)
        assert fm["org"] == "futureself"

    def test_sample_to_variables(self):
        prompty = """---
name: test
sample:
  name: Alice
  role: helper
---
Hi {{ name }}"""

        fm, body = prompty_to_md(prompty)
        assert fm["variables"]["name"] == "Alice"
        assert fm["variables"]["role"] == "helper"

    def test_no_front_matter(self):
        fm, body = prompty_to_md("Just plain text")
        assert fm == {}
        assert body == "Just plain text"

    def test_invalid_yaml(self):
        fm, body = prompty_to_md("---\n: invalid: yaml: {{{\n---\nBody")
        assert fm == {}


class TestRoundTrip:
    def test_round_trip_basic(self):
        original_fm = {
            "name": "round-trip",
            "description": "Test round-trip",
            "version": "1.2.3",
            "tags": ["test"],
        }
        original_body = "Hello {{ name }}!"

        prompty = md_to_prompty(original_fm, original_body)
        recovered_fm, recovered_body = prompty_to_md(prompty)

        assert recovered_fm["name"] == "round-trip"
        assert recovered_fm["description"] == "Test round-trip"
        assert recovered_fm["version"] == "1.2.3"
        assert recovered_fm["tags"] == ["test"]
        assert "Hello {{ name }}!" in recovered_body

    def test_round_trip_with_model(self):
        original_fm = {
            "name": "model-rt",
            "model": {"default": "claude-3", "temperature": 0.8},
        }
        original_body = "System prompt"

        prompty = md_to_prompty(original_fm, original_body)
        recovered_fm, recovered_body = prompty_to_md(prompty)

        assert recovered_fm["model"]["default"] == "claude-3"
        assert recovered_fm["model"]["temperature"] == 0.8
