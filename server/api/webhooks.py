"""GitHub webhook handler for push event-driven re-indexing."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from server.db.database import get_db
from server.db.queries import applications as app_queries
from server.services.cache_service import prompt_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request):
    """Receive GitHub push events and trigger re-indexing of changed .md files."""
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Determine repo
    repo_full_name = payload.get("repository", {}).get("full_name")
    if not repo_full_name:
        return {"ok": True, "message": "No repository in payload"}

    # Find matching app
    db = await get_db()
    async with db.execute(
        "SELECT * FROM applications WHERE github_repo = ?", (repo_full_name,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            logger.info("Webhook for unknown repo: %s", repo_full_name)
            return {"ok": True, "message": "No matching application"}
        app = dict(row)

    # Verify webhook signature
    webhook_secret = app.get("webhook_secret")
    if webhook_secret:
        expected = "sha256=" + hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Process push event
    event = request.headers.get("x-github-event", "")
    if event != "push":
        return {"ok": True, "message": f"Ignoring event: {event}"}

    # Find changed .md files
    commits = payload.get("commits", [])
    changed_files: set[str] = set()
    removed_files: set[str] = set()

    for commit in commits:
        for f in commit.get("added", []) + commit.get("modified", []):
            if f.endswith(".md"):
                changed_files.add(f)
        for f in commit.get("removed", []):
            if f.endswith(".md"):
                removed_files.add(f)

    if not changed_files and not removed_files:
        return {"ok": True, "message": "No .md files changed"}

    # Process async (import here to avoid circular)
    from server.services.sync_service import sync_single_file, remove_file
    from server.services.github_service import GitHubService

    # We need a GitHub token to fetch file content. Use a stored service token or the app webhook context.
    # For now, get the first admin user's token for this org.
    async with db.execute(
        """SELECT u.access_token_encrypted FROM users u
           JOIN org_memberships om ON om.user_id = u.id
           WHERE om.org_id = ? AND om.role = 'admin'
           LIMIT 1""",
        (app["org_id"],),
    ) as cursor:
        token_row = await cursor.fetchone()

    if not token_row or not token_row["access_token_encrypted"]:
        logger.warning("No admin token available for org %s, skipping sync", app["org_id"])
        return {"ok": True, "message": "No token available for sync"}

    from server.utils.crypto import decrypt
    gh = GitHubService(decrypt(token_row["access_token_encrypted"]))

    synced = 0
    try:
        for file_path in changed_files:
            try:
                await sync_single_file(db, app, file_path, gh)
                synced += 1
            except Exception as e:
                logger.error("Failed to sync %s: %s", file_path, e)

        for file_path in removed_files:
            try:
                await remove_file(db, app["id"], file_path)
            except Exception as e:
                logger.error("Failed to remove %s: %s", file_path, e)
    finally:
        gh.close()

    # Invalidate cache for affected prompts
    prompt_cache.clear()

    logger.info("Webhook processed: %d files synced, %d removed", synced, len(removed_files))
    return {"ok": True, "synced": synced, "removed": len(removed_files)}
