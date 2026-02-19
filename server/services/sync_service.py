"""Sync service: indexes GitHub .md files into SQLite for fast search/filtering."""

from __future__ import annotations

import json
import logging

import aiosqlite

from server.db.queries import prompts as prompt_queries
from server.db.queries import applications as app_queries
from server.services.github_service import GitHubService
from server.utils.front_matter import parse_prompt_file, body_hash, ensure_id, front_matter_to_json, extract_tags

logger = logging.getLogger(__name__)


async def sync_app(db: aiosqlite.Connection, app: dict, github: GitHubService) -> int:
    """Full sync: index all .md files in a GitHub repo/subdirectory into SQLite.

    Returns count of prompts synced.
    """
    repo = app["github_repo"]
    subdir = app.get("subdirectory", "")
    branch = app.get("default_branch", "main")

    logger.info("Syncing app %s from %s (branch: %s, subdir: %s)", app["id"], repo, branch, subdir)

    md_files = github.list_md_files(repo, subdirectory=subdir, branch=branch)
    synced = 0

    for md_file in md_files:
        try:
            content, file_sha = github.get_file_content(repo, md_file["path"], branch=branch)
            await _index_prompt_file(db, app["id"], md_file["path"], content, file_sha)
            synced += 1
        except Exception as e:
            logger.error("Failed to sync file %s: %s", md_file["path"], e)

    await app_queries.update_sync_time(db, app["id"])
    logger.info("Synced %d prompts for app %s", synced, app["id"])
    return synced


async def sync_single_file(
    db: aiosqlite.Connection, app: dict, file_path: str, github: GitHubService
) -> None:
    """Sync a single file from GitHub into SQLite (used by webhook handler)."""
    repo = app["github_repo"]
    branch = app.get("default_branch", "main")

    try:
        content, file_sha = github.get_file_content(repo, file_path, branch=branch)
        await _index_prompt_file(db, app["id"], file_path, content, file_sha)
    except Exception as e:
        logger.error("Failed to sync file %s: %s", file_path, e)
        raise


async def remove_file(db: aiosqlite.Connection, app_id: str, file_path: str) -> None:
    """Remove a prompt from SQLite when its file is deleted from GitHub."""
    async with db.execute(
        "SELECT id FROM prompts WHERE app_id = ? AND file_path = ?", (app_id, file_path)
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            await prompt_queries.delete_prompt(db, row["id"])
            logger.info("Removed prompt %s (file: %s)", row["id"], file_path)


async def _index_prompt_file(
    db: aiosqlite.Connection, app_id: str, file_path: str, content: str, git_sha: str
) -> None:
    """Parse a .md file and upsert its metadata into the prompts table."""
    try:
        fm, body = parse_prompt_file(content)
    except Exception as e:
        logger.warning("Failed to parse front-matter in %s: %s", file_path, e)
        return

    if not fm.get("name"):
        logger.warning("Skipping %s: no 'name' in front-matter", file_path)
        return

    fm = ensure_id(fm)

    model_config = fm.get("model", {})
    modality = fm.get("modality", {})

    data = {
        "id": fm["id"],
        "app_id": app_id,
        "name": fm["name"],
        "file_path": file_path,
        "domain": fm.get("domain"),
        "description": fm.get("description"),
        "type": fm.get("type", "chat"),
        "modality_input": modality.get("input", "text") if isinstance(modality, dict) else "text",
        "modality_output": modality.get("output", "text") if isinstance(modality, dict) else "text",
        "default_model": model_config.get("default") if isinstance(model_config, dict) else None,
        "environment": fm.get("environment", "development"),
        "tags": extract_tags(fm),
        "active": fm.get("active", True),
        "version": fm.get("version"),
        "git_sha": git_sha,
        "front_matter": front_matter_to_json(fm),
        "body_hash": body_hash(body),
        "body": body,
    }

    await prompt_queries.upsert_prompt(db, data)
