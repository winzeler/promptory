"""Admin API routes — CRUD operations, requires GitHub SSO session."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse

from server.db.database import get_db
from server.db.queries import organizations as org_queries
from server.db.queries import applications as app_queries
from server.db.queries import prompts as prompt_queries
from server.db.queries import analytics as analytics_queries
from server.services.github_service import GitHubService
from server.services.prompt_service import (
    create_prompt,
    update_prompt,
    delete_prompt_file,
    get_prompt_with_content,
)
from server.services.render_service import render_prompt, render_prompt_with_includes
from server.services.tts_service import (
    synthesize_tts,
    is_tts_configured,
    TTSError,
    TTSNotConfiguredError,
)
from server.services.sync_service import sync_app
from server.services.cache_service import prompt_cache
from server.utils.crypto import decrypt
from server.utils.front_matter import parse_prompt_file, serialize_prompt_file
from server.utils.prompty_converter import md_to_prompty, prompty_to_md

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

    # Concurrent edit detection: if client provides expected_sha, verify it matches
    expected_sha = body.get("expected_sha")
    if expected_sha:
        prompt = await prompt_queries.get_prompt(db, prompt_id)
        if prompt and prompt.get("git_sha") and prompt["git_sha"] != expected_sha:
            gh.close()
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "CONFLICT",
                        "message": "Prompt was modified by another user. Refresh and try again.",
                        "current_sha": prompt["git_sha"],
                        "expected_sha": expected_sha,
                    }
                },
            )

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


@router.get("/prompts/{prompt_id}/at/{sha}")
async def get_prompt_at_sha(prompt_id: str, sha: str, request: Request):
    """Fetch full prompt content at a specific git commit SHA."""
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
        content, blob_sha = gh.get_file_content_at_sha(
            app["github_repo"], prompt["file_path"], sha
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": str(e)}})
    finally:
        gh.close()

    fm, body = parse_prompt_file(content)
    return {"sha": sha, "front_matter": fm, "body": body, "raw": content}


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


# ── Batch Operations ──

@router.post("/prompts/batch")
async def batch_update_prompts(request: Request):
    """Batch update fields across multiple prompts in a single commit."""
    user = _require_user(request)
    db = await get_db()
    body = await request.json()

    prompt_ids = body.get("prompt_ids", [])
    action = body.get("action", "update_field")
    field = body.get("field")
    value = body.get("value")
    commit_message = body.get("commit_message", "Batch update prompts")

    if not prompt_ids:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "prompt_ids is required"}})
    if action == "update_field" and not field:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "field is required for update_field action"}})

    allowed_fields = {"environment", "tags", "model.default", "active"}
    if field and field not in allowed_fields:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": f"field must be one of: {', '.join(sorted(allowed_fields))}"}})

    # Validate all prompts exist and belong to the same app
    prompts = []
    app_ids = set()
    for pid in prompt_ids:
        p = await prompt_queries.get_prompt(db, pid)
        if not p:
            raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"Prompt not found: {pid}"}})
        prompts.append(p)
        app_ids.add(p["app_id"])

    if len(app_ids) > 1:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "All prompts must belong to the same application"}})

    app_id = app_ids.pop()
    app = await app_queries.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail={"error": {"code": "APP_NOT_FOUND", "message": "App not found"}})

    gh = _get_github_for_user(user)
    try:
        files_to_update = []
        for p in prompts:
            content, _ = gh.get_file_content(
                app["github_repo"], p["file_path"],
                branch=app.get("default_branch", "main"),
            )
            fm, body_text = parse_prompt_file(content)

            # Apply field update
            if field == "environment":
                fm["environment"] = value
            elif field == "tags":
                fm["tags"] = value
            elif field == "model.default":
                if "model" not in fm or not isinstance(fm["model"], dict):
                    fm["model"] = {}
                fm["model"]["default"] = value
            elif field == "active":
                fm["active"] = value

            new_content = serialize_prompt_file(fm, body_text)
            files_to_update.append({"path": p["file_path"], "content": new_content})

        commit_sha = gh.create_or_update_files(
            app["github_repo"],
            files_to_update,
            commit_message=commit_message,
            branch=app.get("default_branch", "main"),
            author_name=user.get("name") or user.get("login"),
            author_email=user.get("email"),
        )
    finally:
        gh.close()

    # Re-sync affected prompts
    gh2 = _get_github_for_user(user)
    try:
        await sync_app(db, app, gh2)
    finally:
        gh2.close()

    # Invalidate caches
    for pid in prompt_ids:
        prompt_cache.invalidate(f"id:{pid}")

    return {"ok": True, "updated": len(prompts), "commit_sha": commit_sha}


@router.post("/prompts/batch-delete")
async def batch_delete_prompts(request: Request):
    """Delete multiple prompts in a single commit."""
    user = _require_user(request)
    db = await get_db()
    body = await request.json()

    prompt_ids = body.get("prompt_ids", [])
    commit_message = body.get("commit_message", "Batch delete prompts")

    if not prompt_ids:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "prompt_ids is required"}})

    # Validate all prompts exist and belong to same app
    prompts = []
    app_ids = set()
    for pid in prompt_ids:
        p = await prompt_queries.get_prompt(db, pid)
        if not p:
            raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": f"Prompt not found: {pid}"}})
        prompts.append(p)
        app_ids.add(p["app_id"])

    if len(app_ids) > 1:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "All prompts must belong to the same application"}})

    app_id = app_ids.pop()
    app = await app_queries.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404)

    gh = _get_github_for_user(user)
    try:
        # Use Git Trees API to delete all files in one commit
        # (set content to empty blob with mode 100644 won't work — use delete_file per file for now,
        #  or better: create tree without these paths)
        for p in prompts:
            _, file_sha = gh.get_file_content(
                app["github_repo"], p["file_path"],
                branch=app.get("default_branch", "main"),
            )
            gh.delete_file(
                app["github_repo"], p["file_path"],
                commit_message=commit_message,
                sha=file_sha,
                branch=app.get("default_branch", "main"),
            )
    finally:
        gh.close()

    # Delete from DB
    for p in prompts:
        await prompt_queries.delete_prompt(db, p["id"])
        prompt_cache.invalidate(f"id:{p['id']}")

    return {"ok": True, "deleted": len(prompts)}


# ── Prompty Import/Export ──

@router.get("/prompts/{prompt_id}/export/prompty")
async def export_prompty(prompt_id: str, request: Request):
    """Export a prompt in .prompty format."""
    user = _require_user(request)
    db = await get_db()

    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}})

    fm = json.loads(prompt.get("front_matter", "{}"))
    body = fm.pop("_body", "")

    # Ensure name is in front-matter for export
    if not fm.get("name"):
        fm["name"] = prompt["name"]

    prompty_content = md_to_prompty(fm, body)
    filename = f"{prompt['name']}.prompty"

    return PlainTextResponse(
        content=prompty_content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/prompts/import/prompty")
async def import_prompty(request: Request):
    """Import a .prompty file and create a .md prompt in GitHub."""
    user = _require_user(request)
    db = await get_db()
    body = await request.json()

    prompty_content = body.get("content")
    app_id = body.get("app_id")
    if not prompty_content or not app_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "content and app_id are required"}})

    app = await app_queries.get_app(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail={"error": {"code": "APP_NOT_FOUND", "message": "App not found"}})

    fm, prompt_body = prompty_to_md(prompty_content)

    # Use name from front-matter or generate one
    name = fm.get("name")
    if not name:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "Prompty file must have a name field"}})

    # Build create payload
    create_data = {
        "app_id": app_id,
        "name": name,
        "body": prompt_body,
        "front_matter": fm,
        "commit_message": f"Import {name} from .prompty",
    }

    gh = _get_github_for_user(user)
    try:
        result = await create_prompt(db, create_data, gh, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}})
    finally:
        gh.close()

    return result


# ── Analytics ──

@router.get("/analytics/requests-per-day")
async def analytics_requests_per_day(request: Request, app_id: str | None = None, days: int = 30):
    _require_user(request)
    db = await get_db()
    data = await analytics_queries.requests_per_day(db, app_id=app_id, days=days)
    return {"items": data}


@router.get("/analytics/cache-hit-rate")
async def analytics_cache_hit_rate(request: Request, app_id: str | None = None, days: int = 30):
    _require_user(request)
    db = await get_db()
    data = await analytics_queries.cache_hit_rate(db, app_id=app_id, days=days)
    return {"items": data}


@router.get("/analytics/latency")
async def analytics_latency(request: Request, app_id: str | None = None, days: int = 7):
    _require_user(request)
    db = await get_db()
    data = await analytics_queries.latency_percentiles(db, app_id=app_id, days=days)
    return {"items": data}


@router.get("/analytics/top-prompts")
async def analytics_top_prompts(request: Request, app_id: str | None = None, days: int = 30, limit: int = 10):
    _require_user(request)
    db = await get_db()
    data = await analytics_queries.top_prompts(db, app_id=app_id, days=days, limit=limit)
    return {"items": data}


@router.get("/analytics/usage-by-key")
async def analytics_usage_by_key(request: Request, days: int = 30, limit: int = 10):
    _require_user(request)
    db = await get_db()
    data = await analytics_queries.usage_by_api_key(db, days=days, limit=limit)
    return {"items": data}


# ── TTS ──

@router.get("/tts/status")
async def tts_status(request: Request):
    """Check whether TTS synthesis is configured on the server."""
    _require_user(request)
    configured = is_tts_configured()
    return {"configured": configured, "provider": "elevenlabs" if configured else None}


@router.post("/prompts/{prompt_id}/tts-preview")
async def tts_preview(prompt_id: str, request: Request):
    """Render a prompt and synthesize TTS audio preview."""
    _require_user(request)
    db = await get_db()

    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}},
        )

    body_data = await request.json()
    variables = body_data.get("variables", {})
    tts_config = body_data.get("tts_config", {})

    # Render the prompt body with variables (use includes if prompt has them)
    prompt_body = prompt.get("body", "")
    fm = json.loads(prompt.get("front_matter", "{}"))
    includes = fm.get("includes", [])

    try:
        if includes:
            rendered_body = await render_prompt_with_includes(
                prompt_body, variables, db, prompt["app_id"]
            )
        else:
            rendered_body = render_prompt(prompt_body, variables)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "RENDER_ERROR", "message": str(e)}},
        )

    # If TTS is not configured, return 503 with rendered body so client can still display it
    if not is_tts_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "TTS_NOT_CONFIGURED",
                    "message": "ElevenLabs API key not configured on server",
                    "rendered_body": rendered_body,
                }
            },
        )

    try:
        audio_url = await synthesize_tts(rendered_body, tts_config)
    except TTSNotConfiguredError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "TTS_NOT_CONFIGURED",
                    "message": "ElevenLabs API key not configured",
                    "rendered_body": rendered_body,
                }
            },
        )
    except TTSError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "TTS_SYNTHESIS_FAILED", "message": str(e)}},
        )

    # S3 presigned URLs start with https:// — redirect the client
    if audio_url.startswith("https://"):
        return RedirectResponse(audio_url, status_code=302)
    # Local filesystem — serve file directly
    return FileResponse(audio_url, media_type="audio/mpeg")


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
