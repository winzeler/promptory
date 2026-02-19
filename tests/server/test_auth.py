"""Tests for authentication and rate limiting."""

from __future__ import annotations

import pytest

from tests.conftest import PROMPT_ID


@pytest.mark.asyncio
async def test_api_key_valid(client, test_api_key):
    resp = await client.get(
        f"/api/v1/prompts/{PROMPT_ID}",
        headers={"Authorization": f"Bearer {test_api_key}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_invalid(client):
    resp = await client.get(
        f"/api/v1/prompts/{PROMPT_ID}",
        headers={"Authorization": "Bearer pm_live_invalid_key_12345"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rate_limiter_429(app, db):
    """Lower the rate limit, exceed it, and expect 429."""
    from httpx import ASGITransport, AsyncClient
    from server.auth.rate_limiter import RateLimitMiddleware

    # Walk middleware stack and set a very low limit for this test
    obj = app.middleware_stack
    while obj is not None:
        if isinstance(obj, RateLimitMiddleware):
            obj._windows.clear()
            obj.limit = 5  # only 5 requests allowed
            break
        obj = getattr(obj, "app", None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from tests.conftest import API_KEY_RAW
        headers = {"Authorization": f"Bearer {API_KEY_RAW}"}

        responses = []
        for _ in range(10):
            r = await client.get(f"/api/v1/prompts/{PROMPT_ID}", headers=headers)
            responses.append(r.status_code)

        assert 429 in responses, f"Expected 429 in responses, got: {responses}"

        # Check Retry-After header on 429
        last = await client.get(f"/api/v1/prompts/{PROMPT_ID}", headers=headers)
        if last.status_code == 429:
            assert "retry-after" in last.headers

    # Restore default
    obj = app.middleware_stack
    while obj is not None:
        if isinstance(obj, RateLimitMiddleware):
            obj.limit = 100
            obj._windows.clear()
            break
        obj = getattr(obj, "app", None)
