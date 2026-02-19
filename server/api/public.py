"""Public API routes for prompt fetching — used by SDK and LLM services."""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request, Response

from server.db.database import get_db
from server.db.queries import prompts as prompt_queries
from server.services.prompt_service import get_prompt_with_content, get_prompt_by_name_with_content
from server.services.github_service import GitHubService
from server.services.render_service import render_prompt, render_prompt_with_includes
from server.services.cache_service import prompt_cache
from server.utils.crypto import decrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


def _get_github(request: Request) -> GitHubService:
    """Get a GitHubService using the API key owner's token, or a default if available."""
    # For API key auth, we need a GitHub token. Use the key owner's token.
    api_key = getattr(request.state, "api_key", None)
    if api_key and api_key.get("user_id"):
        # We'd need to look up the user's token. For now, use the key holder context.
        pass
    # Fall back: will be set up during app lifespan with a service account token
    raise HTTPException(status_code=500, detail="GitHub service unavailable")


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str, request: Request, response: Response):
    """Fetch a prompt by UUID."""
    start = time.time()
    if_none_match = request.headers.get("if-none-match")

    # Check cache
    cached, etag, is_fresh = prompt_cache.get(f"id:{prompt_id}")
    if cached and is_fresh:
        if if_none_match and if_none_match == etag:
            _log_access(request, prompt_id, cached.get("name"), True, start)
            return Response(status_code=304)
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        _log_access(request, prompt_id, cached.get("name"), True, start)
        return cached

    # Cache miss — fetch from DB + GitHub
    db = await get_db()
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"No prompt found with id '{prompt_id}'"}})

    # Build response from SQLite metadata (avoid GitHub API call for basic fetch)
    fm = json.loads(prompt.get("front_matter", "{}"))
    tags = prompt.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    result = {
        "id": prompt["id"],
        "name": prompt["name"],
        "version": fm.get("version", prompt.get("version", "")),
        "org": fm.get("org", ""),
        "app": fm.get("app", ""),
        "domain": prompt.get("domain"),
        "description": prompt.get("description"),
        "type": prompt.get("type", "chat"),
        "role": fm.get("role", "system"),
        "model": fm.get("model", {}),
        "modality": fm.get("modality"),
        "tts": fm.get("tts"),
        "audio": fm.get("audio"),
        "environment": prompt.get("environment", "development"),
        "active": bool(prompt.get("active", True)),
        "tags": tags,
        "body": fm.get("_body", ""),  # Body cached in front_matter JSON
        "includes": fm.get("includes", []),
        "git_sha": prompt.get("git_sha"),
        "updated_at": prompt.get("updated_at"),
    }

    # Cache it
    etag = f'"{result.get("version", "0")}-{(result.get("git_sha") or "")[:8]}"'
    prompt_cache.put(f"id:{prompt_id}", result, etag)

    if if_none_match and if_none_match == etag:
        _log_access(request, prompt_id, result.get("name"), False, start)
        return Response(status_code=304)

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    _log_access(request, prompt_id, result.get("name"), False, start)
    return result


@router.get("/by-name/{org}/{app_name}/{name}")
async def get_prompt_by_name(
    org: str, app_name: str, name: str,
    request: Request, response: Response,
    environment: str | None = None,
):
    """Fetch a prompt by its fully qualified name (org/app/name)."""
    start = time.time()
    cache_key = f"name:{org}/{app_name}/{name}:{environment or 'any'}"
    if_none_match = request.headers.get("if-none-match")

    # Check cache
    cached, etag, is_fresh = prompt_cache.get(cache_key)
    if cached and is_fresh:
        if if_none_match and if_none_match == etag:
            _log_access(request, cached.get("id", ""), name, True, start)
            return Response(status_code=304)
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        _log_access(request, cached.get("id", ""), name, True, start)
        return cached

    # Cache miss
    db = await get_db()
    app = await prompt_queries.find_app_by_org_and_repo(db, org, app_name)
    if not app:
        raise HTTPException(status_code=404, detail={"error": {"code": "APP_NOT_FOUND", "message": f"No app found for {org}/{app_name}"}})

    prompt = await prompt_queries.get_prompt_by_name(db, app["id"], name, environment)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"No prompt found: {org}/{app_name}/{name}"}})

    fm = json.loads(prompt.get("front_matter", "{}"))
    tags = prompt.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    result = {
        "id": prompt["id"],
        "name": prompt["name"],
        "version": fm.get("version", prompt.get("version", "")),
        "org": org,
        "app": app_name,
        "domain": prompt.get("domain"),
        "description": prompt.get("description"),
        "type": prompt.get("type", "chat"),
        "role": fm.get("role", "system"),
        "model": fm.get("model", {}),
        "modality": fm.get("modality"),
        "tts": fm.get("tts"),
        "audio": fm.get("audio"),
        "environment": prompt.get("environment", "development"),
        "active": bool(prompt.get("active", True)),
        "tags": tags,
        "body": fm.get("_body", ""),
        "includes": fm.get("includes", []),
        "git_sha": prompt.get("git_sha"),
        "updated_at": prompt.get("updated_at"),
    }

    etag = f'"{result.get("version", "0")}-{(result.get("git_sha") or "")[:8]}"'
    prompt_cache.put(cache_key, result, etag)
    prompt_cache.put(f"id:{prompt['id']}", result, etag)

    if if_none_match and if_none_match == etag:
        _log_access(request, prompt["id"], name, False, start)
        return Response(status_code=304)

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    _log_access(request, prompt["id"], name, False, start)
    return result


@router.post("/{prompt_id}/render")
async def render_prompt_endpoint(prompt_id: str, request: Request):
    """Render a prompt with Jinja2 template variables."""
    body = await request.json()
    variables = body.get("variables", {})

    db = await get_db()
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"No prompt found with id '{prompt_id}'"}})

    fm = json.loads(prompt.get("front_matter", "{}"))
    template_body = fm.get("_body", "")
    includes = fm.get("includes", [])

    try:
        if includes:
            rendered = await render_prompt_with_includes(
                template_body, variables, db, prompt["app_id"]
            )
        else:
            rendered = render_prompt(template_body, variables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "RENDER_ERROR", "message": str(e)}})

    return {
        "id": prompt["id"],
        "name": prompt["name"],
        "rendered_body": rendered,
        "meta": fm,
        "model": fm.get("model", {}),
    }


def _log_access(request: Request, prompt_id: str, name: str | None, cache_hit: bool, start: float):
    """Fire-and-forget access logging (non-blocking)."""
    import asyncio

    elapsed = int((time.time() - start) * 1000)
    api_key = getattr(request.state, "api_key", None)
    api_key_id = api_key["id"] if api_key else None

    async def _log():
        try:
            db = await get_db()
            await prompt_queries.log_access(
                db, prompt_id, name, api_key_id, None, cache_hit, elapsed,
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
            )
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_log())
    except RuntimeError:
        pass
