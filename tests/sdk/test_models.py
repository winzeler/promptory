"""Tests for SDK Prompt model."""

from __future__ import annotations

import sys
from pathlib import Path

# Add SDK source to path so we can import without installing the SDK package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk" / "src"))

from promptdis.models import Prompt  # noqa: E402


def test_prompt_from_dict():
    data = {
        "id": "p-001",
        "name": "greeting",
        "version": "1.0",
        "org": "testorg",
        "app": "testapp",
        "domain": "onboarding",
        "description": "A greeting prompt",
        "type": "chat",
        "role": "system",
        "model": {"default": "gemini-2.0-flash"},
        "environment": "production",
        "active": True,
        "tags": ["onboarding", "greeting"],
        "body": "Hello {{ name }}!",
        "includes": [],
        "git_sha": "abc123",
        "updated_at": "2025-01-01T00:00:00",
    }
    prompt = Prompt.from_api_response(data)
    assert prompt.id == "p-001"
    assert prompt.name == "greeting"
    assert prompt.domain == "onboarding"
    assert prompt.model == {"default": "gemini-2.0-flash"}
    assert prompt.tags == ["onboarding", "greeting"]
    assert prompt.body == "Hello {{ name }}!"


def test_prompt_from_dict_defaults():
    prompt = Prompt.from_api_response({"id": "p-002", "name": "minimal"})
    assert prompt.version == ""
    assert prompt.type == "chat"
    assert prompt.environment == "development"
    assert prompt.active is True
    assert prompt.body == ""


def test_prompt_render():
    prompt = Prompt(
        id="p-001",
        name="test",
        version="1.0",
        org="o",
        app="a",
        body="Hello {{ name }}, your role is {{ role_name }}.",
    )
    result = prompt.render({"name": "Alice", "role_name": "admin"})
    assert result == "Hello Alice, your role is admin."


def test_prompt_render_no_variables():
    prompt = Prompt(id="p-001", name="test", version="1.0", org="o", app="a", body="Static text.")
    assert prompt.render() == "Static text."
