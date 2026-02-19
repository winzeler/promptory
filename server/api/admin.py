"""Admin API routes — CRUD operations, requires GitHub SSO session."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from server.db.database import get_db
from server.db.queries import organizations as org_queries
from server.db.queries import applications as app_queries
from server.db.queries import prompts as prompt_queries
from server.services.github_service import GitHubService
from server.services.prompt_service import (
    create_prompt,
    update_prompt,
    delete_prompt_file,
    get_prompt_with_content,
)
from server.services.sync_service import sync_app
from server.services.cache_service import prompt_cache
from server.utils.crypto import decrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}})
    return user


def _get_github_for_user(user: dict) -> GitHubService:
    token = user.get("access_token_encrypted")
    if not token:
        raise HTTPException(status_code=500, detail={"error": {"code": "INTERNAL_ERROR", "message": "No GitHub token available"}})
    return GitHubService(decrypt(token))


# ── Organizations ──

@router.get("/orgs")
async def list_orgs(request: Request):
    user = _require_user(request)
    db = await get_db()
    orgs = await org_queries.list_orgs_for_user(db, user["id"])
    return {"items": orgs}


# ── Applications ──

@router.get("/orgs/{org_id}/apps")
async def list_apps(org_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    apps = await app_queries.list_apps_for_org(db, org_id)
    return {"items": apps}


@router.post("/orgs/{org_id}/apps")
async def create_application(org_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    body = await request.json()

    org = await org_queries.get_org(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Organization not found"}})

    github_repo = body.get("github_repo")
    if not github_repo:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "github_repo is required"}})

    # Verify repo exists and user has access
    gh = _get_github_for_user(user)
    try:
        gh.gh.get_repo(github_repo)
    except Exception:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": f"Cannot access repo: {github_repo}"}})
    finally:
        gh.close()

    app_id = await app_queries.create_app(
        db, org_id, github_repo,
        subdirectory=body.get("subdirectory", ""),
        display_name=body.get("display_name"),
        default_branch=body.get("default_branch", "main"),
    )

    app = await app_queries.get_app(db, app_id)
    return app


@router.put("/apps/{app_id}")
async def update_application(app_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    body = await request.json()

    await app_queries.update_app(
        db, app_id,
        display_name=body.get("display_name"),
        default_branch=body.get("default_branch"),
        subdirectory=body.get("subdirectory"),
    )
    return await app_queries.get_app(db, app_id)


@router.delete("/apps/{app_id}")
async def delete_application(app_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    await prompt_queries.delete_prompts_by_app(db, app_id)
    await app_queries.delete_app(db, app_id)
    prompt_cache.clear()
    return {"ok": True}


# ── Prompts ──

@router.get("/apps/{app_id}/prompts")
async def list_prompts(
    app_id: str, request: Request,
    search: str | None = None,
    domain: str | None = None,
    type: str | None = None,
    environment: str | None = None,
    tags: str | None = None,
    active: bool | None = None,
    page: int = 1,
    per_page: int = 50,
):
    _require_user(request)
    db = await get_db()

    tag_list = tags.split(",") if tags else None
    offset = (page - 1) * per_page

    items, total = await prompt_queries.list_prompts(
        db, app_id, search=search, domain=domain, prompt_type=type,
        environment=environment, tags=tag_list, active=active,
        limit=per_page, offset=offset,
    )

    # Parse tags JSON for each item
    for item in items:
        if isinstance(item.get("tags"), str):
            try:
                item["tags"] = json.loads(item["tags"])
            except (json.JSONDecodeError, TypeError):
                item["tags"] = []

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.get("/prompts/{prompt_id}")
async def get_prompt_detail(prompt_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    gh = _get_github_for_user(user)

    try:
        result = await get_prompt_with_content(db, prompt_id, gh)
    finally:
        gh.close()

    if not result:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"Prompt not found: {prompt_id}"}})
    return result


@router.post("/prompts")
async def create_prompt_endpoint(request: Request):
    user = _require_user(request)
    db = await get_db()
    body = await request.json()
    gh = _get_github_for_user(user)

    try:
        result = await create_prompt(db, body, gh, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}})
    finally:
        gh.close()

    return result


@router.put("/prompts/{prompt_id}")
async def update_prompt_endpoint(prompt_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    body = await request.json()
    gh = _get_github_for_user(user)

    try:
        result = await update_prompt(db, prompt_id, body, gh, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}})
    finally:
        gh.close()

    # Invalidate cache
    prompt_cache.invalidate(f"id:{prompt_id}")
    return result


@router.delete("/prompts/{prompt_id}")
async def delete_prompt_endpoint(prompt_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    gh = _get_github_for_user(user)

    try:
        await delete_prompt_file(
            db, prompt_id, gh,
            commit_message=body.get("commit_message", "Delete prompt"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": str(e)}})
    finally:
        gh.close()

    prompt_cache.invalidate(f"id:{prompt_id}")
    return {"ok": True}


@router.get("/prompts/{prompt_id}/history")
async def get_prompt_history(prompt_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}})

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        raise HTTPException(status_code=404, detail={"error": {"code": "APP_NOT_FOUND", "message": "App not found"}})

    gh = _get_github_for_user(user)
    try:
        history = gh.get_file_history(app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main"))
    finally:
        gh.close()

    return {"items": history}


@router.get("/prompts/{prompt_id}/diff/{sha}")
async def get_prompt_diff(prompt_id: str, sha: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404)

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        raise HTTPException(status_code=404)

    gh = _get_github_for_user(user)
    try:
        diff = gh.get_diff(app["github_repo"], prompt["file_path"], sha, branch=app.get("default_branch", "main"))
    finally:
        gh.close()

    return {"diff": diff}


# ── Rollback & Toggle ──

@router.post("/prompts/{prompt_id}/rollback")
async def rollback_prompt(prompt_id: str, request: Request):
    """Rollback a prompt to a previous git commit SHA.

    Fetches file content at the target SHA from GitHub and commits it
    as the new HEAD, effectively restoring the old version.
    """
    user = _require_user(request)
    db = await get_db()
    body = await request.json()
    target_sha = body.get("target_sha")
    if not target_sha:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "target_sha is required"}})

    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}})

    app = await app_queries.get_app(db, prompt["app_id"])
    if not app:
        raise HTTPException(status_code=404, detail={"error": {"code": "APP_NOT_FOUND", "message": "App not found"}})

    gh = _get_github_for_user(user)
    try:
        # Get the file content at the target SHA
        old_content, _ = gh.get_file_content_at_sha(
            app["github_repo"], prompt["file_path"], target_sha
        )
        # Get current file SHA (needed for update)
        _, current_sha = gh.get_file_content(
            app["github_repo"], prompt["file_path"], branch=app.get("default_branch", "main")
        )
        # Commit the old content as a new commit
        new_commit_sha = gh.update_file(
            app["github_repo"],
            prompt["file_path"],
            old_content,
            commit_message=f"Rollback {prompt['name']} to {target_sha[:7]}",
            sha=current_sha,
            branch=app.get("default_branch", "main"),
            author_name=user.get("name") or user.get("login"),
            author_email=user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "ROLLBACK_FAILED", "message": str(e)}})
    finally:
        gh.close()

    # Invalidate cache for this prompt
    prompt_cache.invalidate(f"id:{prompt_id}")

    # Re-sync the prompt from GitHub to update DB metadata
    from server.services.sync_service import sync_app
    gh2 = _get_github_for_user(user)
    try:
        await sync_app(db, app, gh2)
    finally:
        gh2.close()

    # Fetch updated prompt to get new version
    updated = await prompt_queries.get_prompt(db, prompt_id)
    return {
        "ok": True,
        "new_git_sha": new_commit_sha,
        "new_version": updated.get("version", "unknown") if updated else "unknown",
    }


@router.patch("/prompts/{prompt_id}/active")
async def toggle_prompt_active(prompt_id: str, request: Request):
    """Toggle a prompt's active/inactive status."""
    _require_user(request)
    db = await get_db()
    body = await request.json()
    active = body.get("active")
    if active is None:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "active (bool) is required"}})

    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}})

    await db.execute(
        "UPDATE prompts SET active = ?, updated_at = datetime('now') WHERE id = ?",
        (active, prompt_id),
    )
    await db.commit()

    # Invalidate cache for this prompt
    prompt_cache.invalidate(f"id:{prompt_id}")

    return {"ok": True, "active": active}


# ── Sync ──

@router.post("/sync")
async def force_sync_all(request: Request):
    user = _require_user(request)
    db = await get_db()
    gh = _get_github_for_user(user)

    orgs = await org_queries.list_orgs_for_user(db, user["id"])
    total_synced = 0

    try:
        for org in orgs:
            apps = await app_queries.list_apps_for_org(db, org["id"])
            for app in apps:
                count = await sync_app(db, app, gh)
                total_synced += count
    finally:
        gh.close()

    prompt_cache.clear()
    return {"synced": total_synced}


@router.post("/apps/{app_id}/sync")
async def force_sync_app(app_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    app = await app_queries.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404)

    gh = _get_github_for_user(user)
    try:
        count = await sync_app(db, app, gh)
    finally:
        gh.close()

    prompt_cache.clear()
    return {"synced": count}


@router.get("/sync/status")
async def sync_status(request: Request):
    _require_user(request)
    db = await get_db()
    async with db.execute(
        "SELECT id, github_repo, display_name, last_synced_at FROM applications ORDER BY last_synced_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()
    return {"items": [dict(r) for r in rows], "cache_size": prompt_cache.size}
