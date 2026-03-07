"""Tests for GitHub webhook endpoint POST /api/v1/webhooks/github.

Covers payload validation, repo matching, signature verification,
idempotency, event filtering, file sync dispatch, and cache invalidation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import APP_ID, ORG_ID, USER_ID


WEBHOOK_URL = "/api/v1/webhooks/github"
REPO_FULL_NAME = "testorg/testapp"  # matches seed data in conftest


def _push_payload(
    repo: str = REPO_FULL_NAME,
    added: list[str] | None = None,
    modified: list[str] | None = None,
    removed: list[str] | None = None,
) -> dict:
    """Build a minimal GitHub push event payload."""
    commits = []
    if added or modified or removed:
        commits.append({
            "added": added or [],
            "modified": modified or [],
            "removed": removed or [],
        })
    return {
        "repository": {"full_name": repo},
        "commits": commits,
    }


def _sign_payload(body: bytes, secret: str) -> str:
    """Compute X-Hub-Signature-256 header value."""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@pytest_asyncio.fixture
async def wh_client(app):
    """Unauthenticated client for webhook endpoint (no session needed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_json(wh_client):
    resp = await wh_client.post(
        WEBHOOK_URL,
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_no_repository_in_payload(wh_client):
    resp = await wh_client.post(WEBHOOK_URL, json={"something": "else"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "No repository in payload"


@pytest.mark.asyncio
async def test_unknown_repo(wh_client):
    payload = _push_payload(repo="unknown/repo")
    resp = await wh_client.post(WEBHOOK_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["message"] == "No matching application"


# ---------------------------------------------------------------------------
# Event filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_push_event_ignored(wh_client):
    payload = _push_payload()
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={"x-github-event": "pull_request"},
    )
    assert resp.status_code == 200
    assert "Ignoring event" in resp.json()["message"]


@pytest.mark.asyncio
async def test_no_md_files_changed(wh_client):
    payload = _push_payload(modified=["src/app.py", "README.txt"])
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={"x-github-event": "push"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "No .md files changed"


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_signature(wh_client, db):
    secret = "test-webhook-secret"
    await db.execute(
        "UPDATE applications SET webhook_secret = ? WHERE id = ?",
        (secret, APP_ID),
    )
    await db.commit()

    payload = _push_payload(modified=["prompts/greeting.md"])
    body = json.dumps(payload).encode()
    sig = _sign_payload(body, secret)

    with patch("server.services.sync_service.sync_single_file", new_callable=AsyncMock), \
         patch("server.services.github_service.GitHubService"), \
         patch("server.utils.crypto.decrypt", return_value="fake-token"):
        # Need an admin token row for sync to proceed
        await _seed_admin_token(db)
        resp = await wh_client.post(
            WEBHOOK_URL, content=body,
            headers={
                "content-type": "application/json",
                "x-github-event": "push",
                "x-hub-signature-256": sig,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Clean up
    await db.execute("UPDATE applications SET webhook_secret = NULL WHERE id = ?", (APP_ID,))
    await db.commit()


@pytest.mark.asyncio
async def test_invalid_signature_rejected(wh_client, db):
    secret = "test-webhook-secret"
    await db.execute(
        "UPDATE applications SET webhook_secret = ? WHERE id = ?",
        (secret, APP_ID),
    )
    await db.commit()

    payload = _push_payload(modified=["prompts/greeting.md"])
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={
            "x-github-event": "push",
            "x-hub-signature-256": "sha256=invalidsignature",
        },
    )
    assert resp.status_code == 401

    # Clean up
    await db.execute("UPDATE applications SET webhook_secret = NULL WHERE id = ?", (APP_ID,))
    await db.commit()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_delivery_skipped(wh_client, db):
    delivery_id = "delivery-abc-123"

    # Pre-record this delivery
    await db.execute(
        "INSERT INTO webhook_deliveries (delivery_id, app_id, event_type) VALUES (?, ?, ?)",
        (delivery_id, APP_ID, "push"),
    )
    await db.commit()

    payload = _push_payload(modified=["prompts/greeting.md"])
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={
            "x-github-event": "push",
            "x-github-delivery": delivery_id,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Already processed"


# ---------------------------------------------------------------------------
# Sync dispatch — added/modified files
# ---------------------------------------------------------------------------

async def _seed_admin_token(db):
    """Ensure the test user has an admin membership + encrypted token for webhook sync."""
    # Set an encrypted token on the user
    await db.execute(
        "UPDATE users SET access_token_encrypted = ? WHERE id = ?",
        ("encrypted-fake-token", USER_ID),
    )
    # Ensure admin membership exists
    try:
        await db.execute(
            "INSERT INTO org_memberships (user_id, org_id, role) VALUES (?, ?, ?)",
            (USER_ID, ORG_ID, "admin"),
        )
    except Exception:
        await db.execute(
            "UPDATE org_memberships SET role = 'admin' WHERE user_id = ? AND org_id = ?",
            (USER_ID, ORG_ID),
        )
    await db.commit()


@pytest.mark.asyncio
async def test_push_syncs_changed_md_files(wh_client, db):
    await _seed_admin_token(db)

    payload = _push_payload(
        added=["prompts/new.md"],
        modified=["prompts/greeting.md"],
    )

    with patch("server.services.sync_service.sync_single_file", new_callable=AsyncMock) as mock_sync, \
         patch("server.services.github_service.GitHubService"), \
         patch("server.utils.crypto.decrypt", return_value="fake-token"):
        resp = await wh_client.post(
            WEBHOOK_URL, json=payload,
            headers={"x-github-event": "push"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["synced"] == 2
    assert mock_sync.call_count == 2


@pytest.mark.asyncio
async def test_push_removes_deleted_md_files(wh_client, db):
    await _seed_admin_token(db)

    payload = _push_payload(removed=["prompts/old.md"])

    with patch("server.services.sync_service.sync_single_file", new_callable=AsyncMock), \
         patch("server.services.sync_service.remove_file", new_callable=AsyncMock) as mock_remove, \
         patch("server.services.github_service.GitHubService"), \
         patch("server.utils.crypto.decrypt", return_value="fake-token"):
        resp = await wh_client.post(
            WEBHOOK_URL, json=payload,
            headers={"x-github-event": "push"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] == 1
    assert mock_remove.call_count == 1


@pytest.mark.asyncio
async def test_push_ignores_non_md_files(wh_client, db):
    await _seed_admin_token(db)

    payload = _push_payload(
        added=["src/main.py"],
        modified=["package.json"],
        removed=["old.txt"],
    )
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={"x-github-event": "push"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "No .md files changed"


# ---------------------------------------------------------------------------
# No admin token available
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_push_no_admin_token(wh_client, db):
    # Ensure user has no encrypted token
    await db.execute(
        "UPDATE users SET access_token_encrypted = NULL WHERE id = ?",
        (USER_ID,),
    )
    # Remove any admin memberships
    await db.execute(
        "DELETE FROM org_memberships WHERE org_id = ?",
        (ORG_ID,),
    )
    await db.commit()

    payload = _push_payload(modified=["prompts/greeting.md"])
    resp = await wh_client.post(
        WEBHOOK_URL, json=payload,
        headers={"x-github-event": "push"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "No token available for sync"


# ---------------------------------------------------------------------------
# Delivery is recorded after processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delivery_recorded_after_sync(wh_client, db):
    await _seed_admin_token(db)

    delivery_id = "delivery-record-test-456"
    payload = _push_payload(modified=["prompts/greeting.md"])

    with patch("server.services.sync_service.sync_single_file", new_callable=AsyncMock), \
         patch("server.services.github_service.GitHubService"), \
         patch("server.utils.crypto.decrypt", return_value="fake-token"):
        resp = await wh_client.post(
            WEBHOOK_URL, json=payload,
            headers={
                "x-github-event": "push",
                "x-github-delivery": delivery_id,
            },
        )

    assert resp.status_code == 200

    # Verify delivery was recorded
    async with db.execute(
        "SELECT * FROM webhook_deliveries WHERE delivery_id = ?",
        (delivery_id,),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row["app_id"] == APP_ID
