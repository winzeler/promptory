"""Shared test fixtures for Promptdis."""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import bcrypt


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

_migrations_dir = Path(__file__).resolve().parent.parent / "server" / "db" / "migrations"
MIGRATION_SQL = "\n".join(
    f.read_text() for f in sorted(_migrations_dir.glob("*.sql"))
)

# Stable IDs for seed data
ORG_ID = "org-test-001"
APP_ID = "app-test-001"
APP_ID_2 = "app-test-002"
PROMPT_ID = "prompt-test-001"
PROMPT_ID_2 = "prompt-test-002"
USER_ID = "user-test-001"
API_KEY_RAW = "pm_live_testkeyvalue1234567890abcdef"
API_KEY_PREFIX = API_KEY_RAW[:12]
API_KEY_HASH = bcrypt.hashpw(API_KEY_RAW.encode(), bcrypt.gensalt()).decode()
API_KEY_ID = "key-test-001"

# Scoped API key — only has access to APP_ID (app-test-001)
SCOPED_API_KEY_RAW = "pm_live_scopedkeyvalue9876543210xyz"
SCOPED_API_KEY_PREFIX = SCOPED_API_KEY_RAW[:12]
SCOPED_API_KEY_HASH = bcrypt.hashpw(SCOPED_API_KEY_RAW.encode(), bcrypt.gensalt()).decode()
SCOPED_API_KEY_ID = "key-test-002"

FRONT_MATTER = json.dumps({
    "version": "1.0",
    "org": "testorg",
    "app": "testapp",
    "role": "system",
    "model": {"default": "gemini-2.0-flash"},
    "_body": "Hello {{ name }}, welcome to {{ place }}.",
})

FRONT_MATTER_2 = json.dumps({
    "version": "1.0",
    "org": "testorg",
    "app": "otherapp",
    "role": "system",
    "model": {"default": "gemini-2.0-flash"},
    "_body": "Goodbye {{ name }}.",
})


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database with schema + seed data."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(MIGRATION_SQL)
    await conn.commit()

    # Seed data
    await conn.execute(
        "INSERT INTO organizations (id, github_owner, display_name) VALUES (?, ?, ?)",
        (ORG_ID, "testorg", "Test Org"),
    )
    await conn.execute(
        "INSERT INTO applications (id, org_id, github_repo, display_name) VALUES (?, ?, ?, ?)",
        (APP_ID, ORG_ID, "testorg/testapp", "Test App"),
    )
    await conn.execute(
        "INSERT INTO prompts (id, app_id, name, file_path, domain, description, type, front_matter, body_hash, body, version, git_sha, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (PROMPT_ID, APP_ID, "greeting", "prompts/greeting.md", "test", "A greeting prompt", "chat",
         FRONT_MATTER, "abc123", "Hello {{ name }}, welcome to {{ place }}.", "1.0", "deadbeef", 1),
    )
    await conn.execute(
        "INSERT INTO users (id, github_id, github_login, display_name) VALUES (?, ?, ?, ?)",
        (USER_ID, 12345, "testuser", "Test User"),
    )
    await conn.execute(
        "INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, scopes) VALUES (?, ?, ?, ?, ?, ?)",
        (API_KEY_ID, USER_ID, API_KEY_HASH, API_KEY_PREFIX, "test-key", None),
    )

    # Second application + prompt for cross-app scope testing
    await conn.execute(
        "INSERT INTO applications (id, org_id, github_repo, display_name) VALUES (?, ?, ?, ?)",
        (APP_ID_2, ORG_ID, "testorg/otherapp", "Other App"),
    )
    await conn.execute(
        "INSERT INTO prompts (id, app_id, name, file_path, domain, description, type, front_matter, body_hash, body, version, git_sha, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (PROMPT_ID_2, APP_ID_2, "farewell", "prompts/farewell.md", "test", "A farewell prompt", "chat",
         FRONT_MATTER_2, "def456", "Goodbye {{ name }}.", "1.0", "cafebabe", 1),
    )

    # Scoped API key — only has access to APP_ID (app-test-001)
    scoped_scopes = json.dumps({"app_ids": [APP_ID], "permissions": ["read"]})
    await conn.execute(
        "INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, scopes) VALUES (?, ?, ?, ?, ?, ?)",
        (SCOPED_API_KEY_ID, USER_ID, SCOPED_API_KEY_HASH, SCOPED_API_KEY_PREFIX, "scoped-key", scoped_scopes),
    )
    await conn.commit()
    yield conn
    await conn.close()


# ---------------------------------------------------------------------------
# App / client fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app(db):
    """FastAPI app with test DB injected."""
    # Patch database module to return our test DB
    from server.db import database as db_module
    original_db = db_module._db
    db_module._db = db

    from server.main import app as fastapi_app

    # Reset rate limiter state between tests
    from server.auth.rate_limiter import RateLimitMiddleware
    for middleware in fastapi_app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            break
    # Clear the rate limiter windows on the middleware stack
    # The actual middleware instances are in the middleware_stack
    _clear_rate_limiter(fastapi_app)

    yield fastapi_app

    db_module._db = original_db


def _clear_rate_limiter(app):
    """Walk the middleware stack and clear any RateLimitMiddleware windows."""
    from server.auth.rate_limiter import RateLimitMiddleware
    obj = app.middleware_stack
    while obj is not None:
        if isinstance(obj, RateLimitMiddleware):
            obj._windows.clear()
            return
        obj = getattr(obj, "app", None)


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_api_key() -> str:
    """Bearer token value for test API key."""
    return API_KEY_RAW


@pytest.fixture
def scoped_api_key() -> str:
    """Bearer token value for scoped API key (access to APP_ID only)."""
    return SCOPED_API_KEY_RAW
