"""Tests for public API endpoints."""

from __future__ import annotations

import pytest

from tests.conftest import PROMPT_ID


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "promptory"


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
