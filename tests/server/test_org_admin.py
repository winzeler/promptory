"""Tests for org management admin endpoints (Sprints 1-4).

Covers DELETE /admin/orgs/{org_id}, POST /admin/orgs/refresh,
and GET /admin/github/oauth-info.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import ORG_ID, USER_ID


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

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
        transport=transport,
        base_url="http://test",
        cookies={"promptdis_session": sid},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def unauth_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _mock_github_for_refresh(
    authorized_orgs=None,
    memberships=None,
    personal_login="testuser",
    personal_avatar="https://avatar.test/u",
    list_orgs_side_effect=None,
):
    """Build a MagicMock that behaves like _get_github_for_user() return value."""
    gh = MagicMock()

    if list_orgs_side_effect:
        gh.list_orgs.side_effect = list_orgs_side_effect
    else:
        gh.list_orgs.return_value = authorized_orgs or []

    gh.list_org_memberships.return_value = memberships or []

    gh_user = MagicMock()
    gh_user.login = personal_login
    gh_user.avatar_url = personal_avatar
    gh.gh.get_user.return_value = gh_user

    return gh


# ---------------------------------------------------------------------------
# DELETE /admin/orgs/{org_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remove_org_success(admin_client, db):
    resp = await admin_client.delete(f"/api/v1/admin/orgs/{ORG_ID}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Verify membership is gone
    async with db.execute(
        "SELECT * FROM org_memberships WHERE user_id = ? AND org_id = ?",
        (USER_ID, ORG_ID),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is None


@pytest.mark.asyncio
async def test_remove_org_not_found(admin_client):
    resp = await admin_client.delete("/api/v1/admin/orgs/nonexistent-org-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_remove_org_unauthorized(unauth_client):
    resp = await unauth_client.delete(f"/api/v1/admin/orgs/{ORG_ID}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /admin/orgs/refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_orgs_success(admin_client):
    mock_gh = _mock_github_for_refresh(
        authorized_orgs=[
            {"login": "acme-corp", "avatar_url": "https://avatar.test/acme", "description": "Acme"},
        ],
        memberships=[
            {"login": "acme-corp", "avatar_url": "https://avatar.test/acme", "state": "active", "role": "member"},
            {"login": "secret-corp", "avatar_url": "https://avatar.test/secret", "state": "active", "role": "admin"},
        ],
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data

    logins = {item["login"] for item in data["items"]}
    assert "testuser" in logins  # personal
    assert "acme-corp" in logins
    assert "secret-corp" in logins

    statuses = {item["login"]: item["status"] for item in data["items"]}
    assert statuses["testuser"] == "authorized"
    assert statuses["acme-corp"] == "authorized"
    assert statuses["secret-corp"] == "restricted"


@pytest.mark.asyncio
async def test_refresh_orgs_detects_restricted(admin_client):
    mock_gh = _mock_github_for_refresh(
        authorized_orgs=[
            {"login": "org-a", "avatar_url": None, "description": "A"},
        ],
        memberships=[
            {"login": "org-a", "avatar_url": None, "state": "active", "role": "member"},
            {"login": "org-b", "avatar_url": None, "state": "active", "role": "member"},
        ],
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")

    assert resp.status_code == 200
    items = resp.json()["items"]
    org_b = next(i for i in items if i["login"] == "org-b")
    assert org_b["status"] == "restricted"
    assert org_b["request_url"] is not None


@pytest.mark.asyncio
async def test_refresh_orgs_syncs_to_db(admin_client, db):
    mock_gh = _mock_github_for_refresh(
        authorized_orgs=[
            {"login": "synced-org", "avatar_url": None, "description": "Synced"},
        ],
        memberships=[
            {"login": "synced-org", "avatar_url": None, "state": "active", "role": "member"},
            {"login": "restricted-org", "avatar_url": None, "state": "active", "role": "admin"},
        ],
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")
    assert resp.status_code == 200

    # Check DB: synced-org should be authorized
    async with db.execute(
        """SELECT om.access_status FROM org_memberships om
           JOIN organizations o ON o.id = om.org_id
           WHERE o.github_owner = ? AND om.user_id = ?""",
        ("synced-org", USER_ID),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row["access_status"] == "authorized"

    # restricted-org should be restricted
    async with db.execute(
        """SELECT om.access_status FROM org_memberships om
           JOIN organizations o ON o.id = om.org_id
           WHERE o.github_owner = ? AND om.user_id = ?""",
        ("restricted-org", USER_ID),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row["access_status"] == "restricted"


@pytest.mark.asyncio
async def test_refresh_orgs_detects_revoked_access(admin_client, db):
    # Pre-seed an org membership as "authorized"
    from server.db.queries import organizations as org_queries
    from server.db.queries import users as user_queries

    org_id = await org_queries.upsert_org(db, github_owner="revoked-corp", display_name="Revoked Corp")
    await user_queries.upsert_org_membership(db, USER_ID, org_id, role="member", access_status="authorized")

    # Refresh where revoked-corp is NOT in authorized or membership lists
    mock_gh = _mock_github_for_refresh(
        authorized_orgs=[],
        memberships=[],
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")
    assert resp.status_code == 200

    # Verify DB: revoked-corp should now be restricted
    async with db.execute(
        """SELECT om.access_status FROM org_memberships om
           JOIN organizations o ON o.id = om.org_id
           WHERE o.github_owner = ? AND om.user_id = ?""",
        ("revoked-corp", USER_ID),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row["access_status"] == "restricted"


@pytest.mark.asyncio
async def test_refresh_orgs_expired_token(admin_client):
    mock_gh = _mock_github_for_refresh(
        list_orgs_side_effect=Exception("401 Bad credentials"),
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")

    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"]["error"]["code"] == "GITHUB_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_orgs_github_error(admin_client):
    mock_gh = _mock_github_for_refresh(
        list_orgs_side_effect=Exception("Something went wrong"),
    )
    with patch("server.api.admin._get_github_for_user", return_value=mock_gh):
        resp = await admin_client.post("/api/v1/admin/orgs/refresh")

    assert resp.status_code == 502
    data = resp.json()
    assert data["detail"]["error"]["code"] == "GITHUB_ERROR"


@pytest.mark.asyncio
async def test_refresh_orgs_unauthorized(unauth_client):
    resp = await unauth_client.post("/api/v1/admin/orgs/refresh")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin/github/oauth-info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oauth_info_success(admin_client):
    resp = await admin_client.get("/api/v1/admin/github/oauth-info")
    assert resp.status_code == 200
    data = resp.json()
    assert "client_id" in data
    assert "manage_url" in data
    assert "scopes" in data
    assert isinstance(data["scopes"], list)


@pytest.mark.asyncio
async def test_oauth_info_unauthorized(unauth_client):
    resp = await unauth_client.get("/api/v1/admin/github/oauth-info")
    assert resp.status_code == 401
