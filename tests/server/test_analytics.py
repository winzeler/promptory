"""Tests for analytics query endpoints and database queries."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import ORG_ID, APP_ID, PROMPT_ID, USER_ID
from server.db.queries import analytics as analytics_queries


# ---------------------------------------------------------------------------
# Helper — seed access log data
# ---------------------------------------------------------------------------

async def _seed_access_log(db, prompt_id=PROMPT_ID, count=10, cache_hit=False, latency=50):
    """Insert N rows into prompt_access_log for testing."""
    for i in range(count):
        await db.execute(
            """INSERT INTO prompt_access_log
               (prompt_id, prompt_name, api_key_id, cache_hit, response_time_ms, client_ip, created_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now', ? || ' days'))""",
            (prompt_id, "test-prompt", "key-test-001", 1 if cache_hit else 0, latency + i, "127.0.0.1", f"-{i}"),
        )
    await db.commit()


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
        transport=transport, base_url="http://test",
        cookies={"promptdis_session": sid},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Unit tests for analytics queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_requests_per_day_empty(db):
    result = await analytics_queries.requests_per_day(db)
    assert result == []


@pytest.mark.asyncio
async def test_requests_per_day_with_data(db):
    await _seed_access_log(db, count=5)
    result = await analytics_queries.requests_per_day(db)
    assert len(result) > 0
    assert "day" in result[0]
    assert "count" in result[0]
    total = sum(r["count"] for r in result)
    assert total == 5


@pytest.mark.asyncio
async def test_requests_per_day_with_app_filter(db):
    await _seed_access_log(db, count=3)
    result = await analytics_queries.requests_per_day(db, app_id=APP_ID)
    total = sum(r["count"] for r in result)
    assert total == 3


@pytest.mark.asyncio
async def test_cache_hit_rate_empty(db):
    result = await analytics_queries.cache_hit_rate(db)
    assert result == []


@pytest.mark.asyncio
async def test_cache_hit_rate_with_data(db):
    await _seed_access_log(db, count=4, cache_hit=True)
    await _seed_access_log(db, count=6, cache_hit=False)
    result = await analytics_queries.cache_hit_rate(db)
    # Aggregated across all days
    total_hits = sum(r["hits"] for r in result)
    assert total_hits == 4


@pytest.mark.asyncio
async def test_latency_percentiles(db):
    await _seed_access_log(db, count=5, latency=100)
    result = await analytics_queries.latency_percentiles(db)
    assert len(result) > 0
    assert "avg_ms" in result[0]


@pytest.mark.asyncio
async def test_top_prompts(db):
    await _seed_access_log(db, count=10)
    result = await analytics_queries.top_prompts(db, limit=5)
    assert len(result) >= 1
    assert result[0]["prompt_id"] == PROMPT_ID
    assert result[0]["request_count"] == 10


@pytest.mark.asyncio
async def test_usage_by_api_key(db):
    await _seed_access_log(db, count=5)
    result = await analytics_queries.usage_by_api_key(db, limit=5)
    assert len(result) >= 1
    assert result[0]["request_count"] == 5


# ---------------------------------------------------------------------------
# Integration tests — analytics API endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_requests_per_day_empty(admin_client):
    resp = await admin_client.get("/api/v1/admin/analytics/requests-per-day")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_api_requests_per_day_with_data(admin_client, db):
    await _seed_access_log(db, count=3)
    resp = await admin_client.get("/api/v1/admin/analytics/requests-per-day")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_api_cache_hit_rate(admin_client):
    resp = await admin_client.get("/api/v1/admin/analytics/cache-hit-rate")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_api_latency(admin_client):
    resp = await admin_client.get("/api/v1/admin/analytics/latency")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_api_top_prompts(admin_client, db):
    await _seed_access_log(db, count=5)
    resp = await admin_client.get("/api/v1/admin/analytics/top-prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_api_usage_by_key(admin_client):
    resp = await admin_client.get("/api/v1/admin/analytics/usage-by-key")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_analytics_unauthorized(client):
    resp = await client.get("/api/v1/admin/analytics/requests-per-day")
    assert resp.status_code == 401
