"""Tests for admin API endpoints.

Tests admin CRUD operations: orgs, apps, prompts (list with filters,
detail, toggle active), sync status. GitHub-dependent endpoints (create,
update, delete, history, diff, rollback) are tested with mocked GitHub service.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import ORG_ID, APP_ID, PROMPT_ID, USER_ID


# ---------------------------------------------------------------------------
# Helper — create session and build an authenticated client
# ---------------------------------------------------------------------------

async def _create_session(db, user_id: str = USER_ID) -> str:
    """Insert a session row and return the session ID."""
    import secrets
    sid = secrets.token_hex(24)
    await db.execute(
        "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, datetime('now', '+1 day'))",
        (sid, user_id),
    )
    await db.commit()
    return sid


@pytest_asyncio.fixture
async def admin_client(app, db):
    """Async HTTP client with a valid session cookie for admin endpoints."""
    sid = await _create_session(db)
    # Add org membership for the test user
    try:
        await db.execute(
            "INSERT INTO org_memberships (user_id, org_id, role) VALUES (?, ?, ?)",
            (USER_ID, ORG_ID, "owner"),
        )
        await db.commit()
    except Exception:
        pass  # Already exists from a previous test

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"promptory_session": sid},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Organization endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orgs_unauthorized(client):
    """Admin endpoints require session auth — no cookie → 401."""
    resp = await client.get("/api/v1/admin/orgs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_orgs(admin_client):
    resp = await admin_client.get("/api/v1/admin/orgs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == ORG_ID


# ---------------------------------------------------------------------------
# Application endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_apps(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/orgs/{ORG_ID}/apps")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == APP_ID


@pytest.mark.asyncio
async def test_update_application(admin_client):
    resp = await admin_client.put(
        f"/api/v1/admin/apps/{APP_ID}",
        json={"display_name": "Updated App Name", "default_branch": "develop"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Updated App Name"
    assert data["default_branch"] == "develop"


@pytest.mark.asyncio
async def test_delete_application(admin_client, db):
    # Create a throwaway app to delete
    await db.execute(
        "INSERT INTO applications (id, org_id, github_repo, display_name) VALUES (?, ?, ?, ?)",
        ("app-delete-me", ORG_ID, "testorg/delete-repo", "Delete Me"),
    )
    await db.commit()

    resp = await admin_client.delete("/api/v1/admin/apps/app-delete-me")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Prompt list / filter / search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_prompts(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["page"] == 1
    assert "items" in data


@pytest.mark.asyncio
async def test_list_prompts_with_domain_filter(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/prompts?domain=test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["domain"] == "test"


@pytest.mark.asyncio
async def test_list_prompts_with_search(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/prompts?search=greeting")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_prompts_empty_result(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/prompts?domain=nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_prompts_pagination(admin_client):
    resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/prompts?page=1&per_page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


# ---------------------------------------------------------------------------
# Prompt detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_prompt_detail(admin_client):
    with patch("server.api.admin.get_prompt_with_content", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {
            "id": PROMPT_ID,
            "name": "greeting",
            "body": "Hello {{ name }}",
            "front_matter": {"version": "1.0"},
        }
        with patch("server.api.admin._get_github_for_user") as mock_gh:
            mock_gh.return_value = MagicMock()
            resp = await admin_client.get(f"/api/v1/admin/prompts/{PROMPT_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == PROMPT_ID
            assert data["name"] == "greeting"


@pytest.mark.asyncio
async def test_get_prompt_detail_not_found(admin_client):
    with patch("server.api.admin.get_prompt_with_content", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = None
        with patch("server.api.admin._get_github_for_user") as mock_gh:
            mock_gh.return_value = MagicMock()
            resp = await admin_client.get("/api/v1/admin/prompts/nonexistent-id")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Toggle active
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_toggle_prompt_active(admin_client):
    resp = await admin_client.patch(
        f"/api/v1/admin/prompts/{PROMPT_ID}/active",
        json={"active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["active"] is False

    # Toggle back on
    resp = await admin_client.patch(
        f"/api/v1/admin/prompts/{PROMPT_ID}/active",
        json={"active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is True


@pytest.mark.asyncio
async def test_toggle_active_missing_field(admin_client):
    resp = await admin_client.patch(
        f"/api/v1/admin/prompts/{PROMPT_ID}/active",
        json={},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_toggle_active_prompt_not_found(admin_client):
    resp = await admin_client.patch(
        "/api/v1/admin/prompts/nonexistent-id/active",
        json={"active": True},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Concurrent edit detection (409 Conflict)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_prompt_conflict(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        resp = await admin_client.put(
            f"/api/v1/admin/prompts/{PROMPT_ID}",
            json={
                "body": "Updated body",
                "expected_sha": "wrong-sha-value",
            },
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error"]["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# Sync operations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_status(admin_client):
    resp = await admin_client.get("/api/v1/admin/sync/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "cache_size" in data


@pytest.mark.asyncio
async def test_force_sync_app_not_found(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        resp = await admin_client.post("/api/v1/admin/apps/nonexistent-app/sync")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Create prompt (mocked GitHub)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_prompt(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        with patch("server.api.admin.create_prompt", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": "new-prompt-id",
                "name": "new_prompt",
                "status": "created",
            }
            resp = await admin_client.post(
                "/api/v1/admin/prompts",
                json={
                    "app_id": APP_ID,
                    "name": "new_prompt",
                    "body": "Hello {{ user }}",
                    "front_matter": {"type": "chat"},
                },
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "new_prompt"


@pytest.mark.asyncio
async def test_create_prompt_validation_error(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        with patch("server.api.admin.create_prompt", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError("name is required")
            resp = await admin_client.post(
                "/api/v1/admin/prompts",
                json={"body": "no name provided"},
            )
            assert resp.status_code == 400
            assert resp.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Delete prompt (mocked GitHub)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_prompt(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        with patch("server.api.admin.delete_prompt_file", new_callable=AsyncMock):
            resp = await admin_client.delete(f"/api/v1/admin/prompts/{PROMPT_ID}")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_delete_prompt_not_found(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_gh.return_value = MagicMock()
        with patch("server.api.admin.delete_prompt_file", new_callable=AsyncMock) as mock_del:
            mock_del.side_effect = ValueError("Prompt not found")
            resp = await admin_client.delete("/api/v1/admin/prompts/nonexistent-id")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# History (mocked GitHub)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_prompt_history(admin_client):
    with patch("server.api.admin._get_github_for_user") as mock_gh:
        mock_service = MagicMock()
        mock_service.get_file_history.return_value = [
            {"sha": "abc123", "message": "Initial commit", "author": "testuser", "date": "2026-01-01T00:00:00"},
            {"sha": "def456", "message": "Update prompt", "author": "testuser", "date": "2026-01-02T00:00:00"},
        ]
        mock_gh.return_value = mock_service

        resp = await admin_client.get(f"/api/v1/admin/prompts/{PROMPT_ID}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["sha"] == "abc123"


@pytest.mark.asyncio
async def test_get_prompt_history_not_found(admin_client):
    resp = await admin_client.get("/api/v1/admin/prompts/nonexistent/history")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TTS endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tts_status(admin_client):
    with patch("server.api.admin.is_tts_configured", return_value=False):
        resp = await admin_client.get("/api/v1/admin/tts/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["provider"] is None


@pytest.mark.asyncio
async def test_tts_status_configured(admin_client):
    with patch("server.api.admin.is_tts_configured", return_value=True):
        resp = await admin_client.get("/api/v1/admin/tts/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["provider"] == "elevenlabs"


@pytest.mark.asyncio
async def test_tts_preview_not_configured(admin_client):
    with patch("server.api.admin.is_tts_configured", return_value=False):
        with patch("server.api.admin.render_prompt", return_value="Rendered text"):
            resp = await admin_client.post(
                f"/api/v1/admin/prompts/{PROMPT_ID}/tts-preview",
                json={"variables": {}, "tts_config": {}},
            )
            assert resp.status_code == 503
            data = resp.json()
            assert data["detail"]["error"]["code"] == "TTS_NOT_CONFIGURED"
            assert "rendered_body" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_tts_preview_prompt_not_found(admin_client):
    resp = await admin_client.post(
        "/api/v1/admin/prompts/nonexistent-id/tts-preview",
        json={"variables": {}, "tts_config": {}},
    )
    assert resp.status_code == 404
