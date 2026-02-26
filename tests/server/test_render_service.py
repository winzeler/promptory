"""Tests for the Jinja2 template render service."""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
import aiosqlite

from server.services.render_service import render_prompt, render_prompt_with_includes


def test_basic_render():
    result = render_prompt("Hello {{ name }}!", {"name": "Alice"})
    assert result == "Hello Alice!"


def test_multiple_variables():
    template = "{{ greeting }}, {{ name }}! Welcome to {{ place }}."
    result = render_prompt(template, {"greeting": "Hi", "name": "Bob", "place": "Promptdis"})
    assert result == "Hi, Bob! Welcome to Promptdis."


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


# ---------------------------------------------------------------------------
# Tests for render_prompt_with_includes (Prompt Composition)
# ---------------------------------------------------------------------------

APP_ID = "app-include-test"


async def _create_include_db():
    """Create an in-memory DB with prompts for include testing."""
    from pathlib import Path
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "server" / "db" / "migrations"
    migration_sql = "\n".join(f.read_text() for f in sorted(migrations_dir.glob("*.sql")))

    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(migration_sql)
    await db.commit()

    # Seed org + app
    await db.execute(
        "INSERT INTO organizations (id, github_owner) VALUES (?, ?)",
        ("org-1", "testorg"),
    )
    await db.execute(
        "INSERT INTO applications (id, org_id, github_repo) VALUES (?, ?, ?)",
        (APP_ID, "org-1", "testorg/app"),
    )

    return db


async def _add_prompt(db, name: str, body: str, app_id: str = APP_ID):
    """Add a prompt to the test DB for include resolution."""
    fm = json.dumps({"_body": body, "name": name})
    await db.execute(
        "INSERT INTO prompts (id, app_id, name, file_path, front_matter, active) VALUES (?, ?, ?, ?, ?, 1)",
        (f"id-{name}", app_id, name, f"prompts/{name}.md", fm),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_render_with_single_include():
    db = await _create_include_db()
    try:
        await _add_prompt(db, "preamble", "You are a helpful assistant.")
        template = '{% include "preamble" %}\nNow help {{ name }}.'
        result = await render_prompt_with_includes(template, {"name": "Alice"}, db, APP_ID)
        assert "You are a helpful assistant." in result
        assert "Now help Alice." in result
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_render_with_nested_include():
    db = await _create_include_db()
    try:
        await _add_prompt(db, "base", "Base rules.")
        await _add_prompt(db, "middle", '{% include "base" %}\nMiddle layer.')
        template = '{% include "middle" %}\nTop level.'
        result = await render_prompt_with_includes(template, {}, db, APP_ID)
        assert "Base rules." in result
        assert "Middle layer." in result
        assert "Top level." in result
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_circular_include_raises():
    db = await _create_include_db()
    try:
        await _add_prompt(db, "a", '{% include "b" %}')
        await _add_prompt(db, "b", '{% include "a" %}')
        with pytest.raises(ValueError, match="Circular include"):
            await render_prompt_with_includes('{% include "a" %}', {}, db, APP_ID)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_max_depth_exceeded():
    db = await _create_include_db()
    try:
        # Create chain: d5 -> d4 -> d3 -> d2 -> d1 -> d0
        for i in range(6):
            if i == 0:
                await _add_prompt(db, "d0", "Bottom")
            else:
                await _add_prompt(db, f"d{i}", f'{{% include "d{i-1}" %}}')
        with pytest.raises(ValueError, match="Include depth exceeded"):
            await render_prompt_with_includes('{% include "d5" %}', {}, db, APP_ID)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_missing_include_raises():
    db = await _create_include_db()
    try:
        with pytest.raises(ValueError, match="Include not found"):
            await render_prompt_with_includes('{% include "nonexistent" %}', {}, db, APP_ID)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_render_with_includes_and_variables():
    db = await _create_include_db()
    try:
        await _add_prompt(db, "header", "Welcome, {{ name }}!")
        template = '{% include "header" %}\nYour role is {{ role }}.'
        result = await render_prompt_with_includes(
            template, {"name": "Bob", "role": "admin"}, db, APP_ID
        )
        assert "Welcome, Bob!" in result
        assert "Your role is admin." in result
    finally:
        await db.close()
