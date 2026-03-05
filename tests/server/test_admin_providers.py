"""API integration tests for provider credential endpoints."""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import APP_ID, USER_ID, ORG_ID


async def _create_session(db, user_id: str = USER_ID) -> str:
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
    """Async HTTP client with a valid session cookie."""
    sid = await _create_session(db)
    try:
        await db.execute(
            "INSERT INTO org_memberships (user_id, org_id, role) VALUES (?, ?, ?)",
            (USER_ID, ORG_ID, "owner"),
        )
        await db.commit()
    except Exception:
        pass
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"promptdis_session": sid},
    ) as ac:
        yield ac


class TestProviderRegistry:
    @pytest.mark.asyncio
    async def test_get_registry(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/providers/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "openai" in data["providers"]
        assert "anthropic" in data["providers"]
        assert "google" in data["providers"]
        assert "elevenlabs" in data["providers"]
        for info in data["providers"].values():
            assert "secret_keys" not in info


class TestAppProviders:
    @pytest.mark.asyncio
    async def test_put_get_delete_lifecycle(self, admin_client):
        # PUT
        resp = await admin_client.put(
            f"/api/v1/admin/apps/{APP_ID}/providers/openai",
            json={"secrets": {"api_key": "sk-test-put"}},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # GET
        resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/providers/openai")
        assert resp.status_code == 200
        data = resp.json()
        assert data["secrets"]["has_api_key"] is True
        assert "sk-test-put" not in json.dumps(data["secrets"])

        # DELETE
        resp = await admin_client.delete(f"/api/v1/admin/apps/{APP_ID}/providers/openai")
        assert resp.status_code == 200

        # GET after delete -> 404
        resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/providers/openai")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_app_providers(self, admin_client):
        await admin_client.put(
            f"/api/v1/admin/apps/{APP_ID}/providers/openai",
            json={"secrets": {"api_key": "sk-1"}},
        )
        await admin_client.put(
            f"/api/v1/admin/apps/{APP_ID}/providers/anthropic",
            json={"secrets": {"api_key": "sk-2"}},
        )
        resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/providers")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 2

    @pytest.mark.asyncio
    async def test_provider_status(self, admin_client):
        await admin_client.put(
            f"/api/v1/admin/apps/{APP_ID}/providers/openai",
            json={"secrets": {"api_key": "sk-status-test"}},
        )
        resp = await admin_client.get(f"/api/v1/admin/apps/{APP_ID}/providers/status")
        assert resp.status_code == 200
        providers = resp.json()["providers"]
        assert providers["openai"]["configured"] is True
        assert providers["openai"]["source"] == "app"


class TestUserProviders:
    @pytest.mark.asyncio
    async def test_put_get_delete_user_provider(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/admin/user/providers/anthropic",
            json={"secrets": {"api_key": "sk-user-anthro"}},
        )
        assert resp.status_code == 200

        resp = await admin_client.get("/api/v1/admin/user/providers/anthropic")
        assert resp.status_code == 200
        assert resp.json()["secrets"]["has_api_key"] is True

        resp = await admin_client.delete("/api/v1/admin/user/providers/anthropic")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_user_providers(self, admin_client):
        await admin_client.put(
            "/api/v1/admin/user/providers/google",
            json={"secrets": {"api_key": "google-key"}},
        )
        resp = await admin_client.get("/api/v1/admin/user/providers")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1


class TestAuthRequired:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/v1/admin/providers/registry")
        assert resp.status_code == 401
