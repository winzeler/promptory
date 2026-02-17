"""Prompt CRUD orchestration — bridges GitHub (source of truth) and SQLite (index)."""

from __future__ import annotations

import json
import logging
import uuid

import aiosqlite

from server.db.queries import prompts as prompt_queries
from server.db.queries import applications as app_queries
from server.services.github_service import GitHubService
from server.services.sync_service import sync_single_file
from server.utils.front_matter import (
    parse_prompt_file,
    serialize_prompt_file,
    ensure_id,
    ensure_version,
    body_hash,
    front_matter_to_json,
    extract_tags,
)
from server.utils.validators import validate_front_matter

logger = logging.getLogger(__name__)


async def get_prompt_with_content(
    db: aiosqlite.Connection, prompt_id: str, github: GitHubService
) -> dict | None:
    """Get full prompt data including body content from GitHub."""
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        return None

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        return None

    try:
        content, _ = github.get_file_content(
            app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main")
        )
        fm, body = parse_prompt_file(content)
        return _build_prompt_response(prompt, fm, body)
    except Exception as e:
        logger.error("Failed to fetch prompt content from GitHub: %s", e)
        # Fall back to metadata-only response
        fm = json.loads(prompt.get("front_matter", "{}"))
        return _build_prompt_response(prompt, fm, "")


async def get_prompt_by_name_with_content(
    db: aiosqlite.Connection,
    org: str,
    app_name: str,
    name: str,
    github: GitHubService,
    environment: str | None = None,
) -> dict | None:
    """Look up a prompt by org/app/name and return full content."""
    app = await prompt_queries.find_app_by_org_and_repo(db, org, app_name)
    if not app:
        return None

    prompt = await prompt_queries.get_prompt_by_name(db, app["id"], name, environment)
    if not prompt:
        return None

    try:
        content, _ = github.get_file_content(
            app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main")
        )
        fm, body = parse_prompt_file(content)
        return _build_prompt_response(prompt, fm, body)
    except Exception as e:
        logger.error("Failed to fetch prompt content: %s", e)
        fm = json.loads(prompt.get("front_matter", "{}"))
        return _build_prompt_response(prompt, fm, "")


async def create_prompt(
    db: aiosqlite.Connection, data: dict, github: GitHubService, user: dict
) -> dict:
    """Create a new prompt: write .md file to GitHub, index in SQLite."""
    app = await app_queries.get_app(db, data["app_id"])
    if not app:
        raise ValueError("Application not found")

    # Build front-matter
    fm = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "version": "1.0.0",
        "org": data.get("org", ""),
        "app": data.get("app", ""),
        "domain": data.get("domain"),
        "description": data.get("description"),
        "model": data.get("model", {"default": "gemini-2.0-flash"}),
        "type": data.get("type", "chat"),
        "role": data.get("role", "system"),
        "modality": data.get("modality"),
        "tts": data.get("tts"),
        "audio": data.get("audio"),
        "environment": data.get("environment", "development"),
        "active": True,
        "tags": data.get("tags", []),
    }

    # Clean None values
    fm = {k: v for k, v in fm.items() if v is not None}

    # Validate
    errors = validate_front_matter(fm)
    if errors:
        raise ValueError(f"Validation errors: {'; '.join(errors)}")

    # Serialize
    body = data.get("body", "")
    file_content = serialize_prompt_file(fm, body)

    # Determine file path
    subdir = app.get("subdirectory", "").strip("/")
    domain = data.get("domain", "")
    if domain:
        file_path = f"{subdir}/{domain}/{data['name']}.md".lstrip("/")
    else:
        file_path = f"{subdir}/{data['name']}.md".lstrip("/")

    # Commit to GitHub
    commit_sha = github.create_file(
        app["github_repo"],
        file_path,
        file_content,
        data.get("commit_message", f"Add prompt: {data['name']}"),
        branch=app.get("default_branch", "main"),
        author_name=user.get("display_name") or user.get("github_login"),
        author_email=user.get("email"),
    )

    # Index in SQLite
    await sync_single_file(db, app, file_path, github)

    prompt = await prompt_queries.get_prompt_by_name(db, app["id"], data["name"])
    return prompt


async def update_prompt(
    db: aiosqlite.Connection, prompt_id: str, data: dict, github: GitHubService, user: dict
) -> dict:
    """Update a prompt: update .md file in GitHub, re-index in SQLite."""
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise ValueError("Prompt not found")

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        raise ValueError("Application not found")

    # Get current file from GitHub
    current_content, current_sha = github.get_file_content(
        app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main")
    )
    current_fm, current_body = parse_prompt_file(current_content)

    # Merge updates
    if data.get("front_matter"):
        current_fm.update(data["front_matter"])

    new_body = data.get("body", current_body)

    # Auto-bump version
    ensure_version(current_fm, bump="patch")

    # Validate
    errors = validate_front_matter(current_fm)
    if errors:
        raise ValueError(f"Validation errors: {'; '.join(errors)}")

    # Serialize and commit
    file_content = serialize_prompt_file(current_fm, new_body)
    github.update_file(
        app["github_repo"],
        prompt["file_path"],
        file_content,
        data.get("commit_message", f"Update prompt: {prompt['name']}"),
        current_sha,
        branch=app.get("default_branch", "main"),
        author_name=user.get("display_name") or user.get("github_login"),
        author_email=user.get("email"),
    )

    # Re-index
    await sync_single_file(db, app, prompt["file_path"], github)

    return await prompt_queries.get_prompt(db, prompt_id)


async def delete_prompt_file(
    db: aiosqlite.Connection, prompt_id: str, github: GitHubService, commit_message: str
) -> None:
    """Delete a prompt file from GitHub and remove from SQLite."""
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise ValueError("Prompt not found")

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        raise ValueError("Application not found")

    _, current_sha = github.get_file_content(
        app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main")
    )

    github.delete_file(
        app["github_repo"],
        prompt["file_path"],
        commit_message,
        current_sha,
        branch=app.get("default_branch", "main"),
    )

    await prompt_queries.delete_prompt(db, prompt_id)


def _build_prompt_response(prompt: dict, fm: dict, body: str) -> dict:
    """Build a unified prompt response dict from SQLite row + parsed front-matter + body."""
    model = fm.get("model", {})
    modality = fm.get("modality", {})
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    return {
        "id": prompt["id"],
        "name": prompt["name"],
        "version": fm.get("version", prompt.get("version", "")),
        "org": fm.get("org", ""),
        "app": fm.get("app", ""),
        "domain": prompt.get("domain"),
        "description": prompt.get("description"),
        "type": prompt.get("type", "chat"),
        "role": fm.get("role", "system"),
        "model": model if isinstance(model, dict) else {"default": model},
        "modality": modality if isinstance(modality, dict) else None,
        "tts": fm.get("tts"),
        "audio": fm.get("audio"),
        "environment": prompt.get("environment", "development"),
        "active": bool(prompt.get("active", True)),
        "tags": tags,
        "body": body,
        "includes": fm.get("includes", []),
        "eval": fm.get("eval"),
        "git_sha": prompt.get("git_sha"),
        "updated_at": prompt.get("updated_at"),
    }
