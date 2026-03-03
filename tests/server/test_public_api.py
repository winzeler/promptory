"""Tests for public API endpoints."""

from __future__ import annotations

import pytest

from tests.conftest import PROMPT_ID, PROMPT_ID_2


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "promptdis"


@pytest.mark.asyncio
async def test_get_prompt_by_id(client, test_api_key):
    resp = await client.get(
        f"/api/v1/prompts/{PROMPT_ID}",
        headers={"Authorization": f"Bearer {test_api_key}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == PROMPT_ID
    assert data["name"] == "greeting"
    assert "body" in data


@pytest.mark.asyncio
async def test_get_prompt_unauthorized(client):
    resp = await client.get(f"/api/v1/prompts/{PROMPT_ID}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_render_prompt(client, test_api_key):
    resp = await client.post(
        f"/api/v1/prompts/{PROMPT_ID}/render",
        headers={"Authorization": f"Bearer {test_api_key}"},
        json={"variables": {"name": "Alice", "place": "Wonderland"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Alice" in data["rendered_body"]
    assert "Wonderland" in data["rendered_body"]


# ---------------------------------------------------------------------------
# Scope enforcement tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scoped_key_can_access_allowed_app(client, scoped_api_key):
    """Scoped key can fetch a prompt in the allowed app."""
    resp = await client.get(
        f"/api/v1/prompts/{PROMPT_ID}",
        headers={"Authorization": f"Bearer {scoped_api_key}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == PROMPT_ID


@pytest.mark.asyncio
async def test_scoped_key_blocked_from_other_app(client, scoped_api_key):
    """Scoped key cannot fetch a prompt in a different app."""
    resp = await client.get(
        f"/api/v1/prompts/{PROMPT_ID_2}",
        headers={"Authorization": f"Bearer {scoped_api_key}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_unscoped_key_accesses_all(client, test_api_key):
    """Unscoped key (scopes=NULL) can access prompts in any app."""
    resp1 = await client.get(
        f"/api/v1/prompts/{PROMPT_ID}",
        headers={"Authorization": f"Bearer {test_api_key}"},
    )
    assert resp1.status_code == 200

    resp2 = await client.get(
        f"/api/v1/prompts/{PROMPT_ID_2}",
        headers={"Authorization": f"Bearer {test_api_key}"},
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_scoped_key_render_blocked(client, scoped_api_key):
    """Scoped key cannot render a prompt in a disallowed app."""
    resp = await client.post(
        f"/api/v1/prompts/{PROMPT_ID_2}/render",
        headers={"Authorization": f"Bearer {scoped_api_key}"},
        json={"variables": {"name": "Bob"}},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scoped_key_by_name_blocked(client, scoped_api_key):
    """Scoped key cannot fetch by name in a disallowed app."""
    resp = await client.get(
        "/api/v1/prompts/by-name/testorg/otherapp/farewell",
        headers={"Authorization": f"Bearer {scoped_api_key}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scoped_key_by_name_allowed(client, scoped_api_key):
    """Scoped key can fetch by name in the allowed app."""
    resp = await client.get(
        "/api/v1/prompts/by-name/testorg/testapp/greeting",
        headers={"Authorization": f"Bearer {scoped_api_key}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "greeting"
