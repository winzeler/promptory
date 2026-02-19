"""Tests for the Jinja2 template render service."""

from __future__ import annotations

import pytest

from server.services.render_service import render_prompt


def test_basic_render():
    result = render_prompt("Hello {{ name }}!", {"name": "Alice"})
    assert result == "Hello Alice!"


def test_multiple_variables():
    template = "{{ greeting }}, {{ name }}! Welcome to {{ place }}."
    result = render_prompt(template, {"greeting": "Hi", "name": "Bob", "place": "Promptory"})
    assert result == "Hi, Bob! Welcome to Promptory."


def test_missing_variable_renders_empty():
    result = render_prompt("Hello {{ name }}!", {})
    assert result == "Hello !"


def test_no_variables_passthrough():
    result = render_prompt("Static prompt with no placeholders.", {})
    assert result == "Static prompt with no placeholders."


def test_filter_upper():
    result = render_prompt("{{ name | upper }}", {"name": "alice"})
    assert result == "ALICE"


def test_filter_default():
    result = render_prompt("{{ name | default('World') }}", {})
    assert result == "World"


def test_conditional():
    template = "{% if formal %}Dear {{ name }}{% else %}Hey {{ name }}{% endif %}"
    assert render_prompt(template, {"formal": True, "name": "Dr. Smith"}) == "Dear Dr. Smith"
    assert render_prompt(template, {"formal": False, "name": "Bob"}) == "Hey Bob"


def test_loop():
    template = "{% for item in items %}{{ item }} {% endfor %}"
    result = render_prompt(template, {"items": ["a", "b", "c"]})
    assert result == "a b c "


def test_invalid_template_raises():
    with pytest.raises(ValueError, match="Template rendering failed"):
        render_prompt("{{ invalid syntax {{", {})


def test_sandbox_blocks_dangerous_operations():
    """Sandboxed env should block access to dangerous attributes."""
    with pytest.raises(ValueError, match="Template rendering failed"):
        render_prompt("{{ ''.__class__.__mro__[1].__subclasses__() }}", {})


def test_multiline_template():
    template = """You are a {{ role }} assistant.

Your task is to help with {{ task }}.

Be {{ tone }}."""
    result = render_prompt(template, {"role": "helpful", "task": "coding", "tone": "concise"})
    assert "helpful" in result
    assert "coding" in result
    assert "concise" in result


def test_trailing_newline_preserved():
    result = render_prompt("Hello\n", {})
    assert result.endswith("\n")
