"""Tests for the sync service (GitHub → SQLite indexing)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from server.db.queries import prompts as prompt_queries
from server.services.sync_service import _index_prompt_file, remove_file, sync_app, sync_single_file

from tests.conftest import APP_ID, ORG_ID


SAMPLE_PROMPT_MD = """---
name: test_sync_prompt
version: 1.0.0
type: chat
description: A test prompt for sync
tags:
  - test
  - sync
model:
  default: gemini-2.0-flash
---
Hello {{ name }}, this is a synced prompt."""


@pytest.mark.asyncio
async def test_index_prompt_file(db):
    """_index_prompt_file should parse front-matter and insert into DB."""
    await _index_prompt_file(db, APP_ID, "prompts/synced.md", SAMPLE_PROMPT_MD, "sha123")

    # Verify prompt was inserted
    async with db.execute(
        "SELECT * FROM prompts WHERE name = 'test_sync_prompt' AND app_id = ?", (APP_ID,)
    ) as cursor:
        row = await cursor.fetchone()

    assert row is not None
    row = dict(row)
    assert row["name"] == "test_sync_prompt"
    assert row["file_path"] == "prompts/synced.md"
    assert row["type"] == "chat"
    assert row["git_sha"] == "sha123"
    assert row["version"] == "1.0.0"
    assert row["description"] == "A test prompt for sync"


@pytest.mark.asyncio
async def test_index_prompt_file_skips_no_name(db):
    """Files without a name in front-matter should be skipped."""
    content = "---\ntype: chat\n---\nNo name here."
    await _index_prompt_file(db, APP_ID, "prompts/noname.md", content, "sha456")

    async with db.execute(
        "SELECT COUNT(*) FROM prompts WHERE file_path = 'prompts/noname.md'"
    ) as cursor:
        count = (await cursor.fetchone())[0]
    assert count == 0


@pytest.mark.asyncio
async def test_index_prompt_file_bad_frontmatter(db):
    """Malformed YAML should not crash; file is skipped."""
    content = "---\n: invalid: yaml: {{{\n---\nBody."
    # Should not raise
    await _index_prompt_file(db, APP_ID, "prompts/bad.md", content, "sha789")


@pytest.mark.asyncio
async def test_index_prompt_file_upsert(db):
    """Re-indexing the same file (with stable id) should update, not duplicate."""
    # Include an explicit id so ensure_id preserves it across calls
    md_with_id = """---
name: upsert_prompt
id: 550e8400-e29b-41d4-a716-446655440000
version: 1.0.0
---
Body v1."""

    await _index_prompt_file(db, APP_ID, "prompts/upsert.md", md_with_id, "sha_v1")

    async with db.execute(
        "SELECT git_sha FROM prompts WHERE id = '550e8400-e29b-41d4-a716-446655440000'"
    ) as cursor:
        row = await cursor.fetchone()
    assert dict(row)["git_sha"] == "sha_v1"

    # Re-index same file with new sha
    await _index_prompt_file(db, APP_ID, "prompts/upsert.md", md_with_id, "sha_v2")

    async with db.execute(
        "SELECT git_sha FROM prompts WHERE id = '550e8400-e29b-41d4-a716-446655440000'"
    ) as cursor:
        row2 = await cursor.fetchone()
    assert dict(row2)["git_sha"] == "sha_v2"

    # Should still be only one row
    async with db.execute(
        "SELECT COUNT(*) FROM prompts WHERE id = '550e8400-e29b-41d4-a716-446655440000'"
    ) as cursor:
        assert (await cursor.fetchone())[0] == 1


@pytest.mark.asyncio
async def test_remove_file(db):
    """remove_file should delete a prompt by file_path."""
    # First index a file
    await _index_prompt_file(db, APP_ID, "prompts/to_delete.md", SAMPLE_PROMPT_MD, "sha_del")

    # Verify it exists
    async with db.execute(
        "SELECT COUNT(*) FROM prompts WHERE file_path = 'prompts/to_delete.md' AND app_id = ?", (APP_ID,)
    ) as cursor:
        assert (await cursor.fetchone())[0] == 1

    # Remove it
    await remove_file(db, APP_ID, "prompts/to_delete.md")

    # Verify it's gone
    async with db.execute(
        "SELECT COUNT(*) FROM prompts WHERE file_path = 'prompts/to_delete.md' AND app_id = ?", (APP_ID,)
    ) as cursor:
        assert (await cursor.fetchone())[0] == 0


@pytest.mark.asyncio
async def test_remove_file_nonexistent(db):
    """remove_file on a non-existent path should be a no-op."""
    await remove_file(db, APP_ID, "prompts/does_not_exist.md")


@pytest.mark.asyncio
async def test_sync_app(db):
    """sync_app should index all .md files returned by GitHubService."""
    mock_github = MagicMock()
    mock_github.list_md_files.return_value = [
        {"path": "prompts/a.md"},
        {"path": "prompts/b.md"},
    ]

    prompt_a = """---
name: prompt_a
version: 1.0.0
---
Prompt A body."""

    prompt_b = """---
name: prompt_b
version: 1.0.0
---
Prompt B body."""

    mock_github.get_file_content.side_effect = [
        (prompt_a, "sha_a"),
        (prompt_b, "sha_b"),
    ]

    app_record = {
        "id": APP_ID,
        "github_repo": "testorg/testapp",
        "subdirectory": "",
        "default_branch": "main",
    }

    synced = await sync_app(db, app_record, mock_github)
    assert synced == 2

    # Verify both prompts exist
    async with db.execute(
        "SELECT COUNT(*) FROM prompts WHERE app_id = ? AND name IN ('prompt_a', 'prompt_b')", (APP_ID,)
    ) as cursor:
        assert (await cursor.fetchone())[0] == 2


@pytest.mark.asyncio
async def test_sync_single_file(db):
    """sync_single_file should index one file from GitHub."""
    mock_github = MagicMock()
    mock_github.get_file_content.return_value = (SAMPLE_PROMPT_MD, "sha_single")

    app_record = {
        "id": APP_ID,
        "github_repo": "testorg/testapp",
        "default_branch": "main",
    }

    await sync_single_file(db, app_record, "prompts/single.md", mock_github)

    async with db.execute(
        "SELECT * FROM prompts WHERE file_path = 'prompts/single.md' AND app_id = ?", (APP_ID,)
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert dict(row)["name"] == "test_sync_prompt"


@pytest.mark.asyncio
async def test_sync_single_file_error(db):
    """sync_single_file should raise when GitHub returns an error."""
    mock_github = MagicMock()
    mock_github.get_file_content.side_effect = Exception("GitHub API error")

    app_record = {
        "id": APP_ID,
        "github_repo": "testorg/testapp",
        "default_branch": "main",
    }

    with pytest.raises(Exception, match="GitHub API error"):
        await sync_single_file(db, app_record, "prompts/fail.md", mock_github)
