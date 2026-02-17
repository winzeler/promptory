"""API key generation and validation."""

from __future__ import annotations

import json
import secrets

import bcrypt

import aiosqlite

from server.db.queries import api_keys as key_queries


def generate_api_key(environment: str = "live") -> tuple[str, str, str]:
    """Generate a new API key. Returns (full_key, key_hash, key_prefix)."""
    raw = secrets.token_urlsafe(36)
    full_key = f"pm_{environment}_{raw}"
    key_prefix = full_key[:12]
    key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt()).decode()
    return full_key, key_hash, key_prefix


async def validate_api_key(db: aiosqlite.Connection, provided_key: str) -> dict | None:
    """Validate an API key. Returns the key record if valid, None otherwise."""
    prefix = provided_key[:12]
    candidates = await key_queries.get_key_by_prefix(db, prefix)

    for candidate in candidates:
        if bcrypt.checkpw(provided_key.encode(), candidate["key_hash"].encode()):
            # Check expiry
            if candidate.get("expires_at"):
                from datetime import datetime, timezone

                expires = datetime.fromisoformat(candidate["expires_at"])
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < datetime.now(timezone.utc):
                    return None

            # Update last used
            await key_queries.update_last_used(db, candidate["id"])
            return candidate

    return None


def parse_scopes(scopes_json: str | None) -> dict:
    """Parse scopes JSON string into dict."""
    if not scopes_json:
        return {"org_ids": [], "app_ids": [], "permissions": ["read"]}
    try:
        return json.loads(scopes_json)
    except (json.JSONDecodeError, TypeError):
        return {"org_ids": [], "app_ids": [], "permissions": ["read"]}


def check_scope(scopes: dict, org_id: str | None = None, app_id: str | None = None, permission: str = "read") -> bool:
    """Check if scopes allow access to a given org/app with a given permission."""
    # Check permission
    permissions = scopes.get("permissions", ["read"])
    if permission not in permissions:
        return False

    # If no org/app restrictions, allow all
    org_ids = scopes.get("org_ids", [])
    app_ids = scopes.get("app_ids", [])

    if org_ids and org_id and org_id not in org_ids:
        return False
    if app_ids and app_id and app_id not in app_ids:
        return False

    return True
