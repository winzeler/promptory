"""CRUD queries for provider_configs table."""

from __future__ import annotations

import json
import uuid

import aiosqlite

from server.utils.crypto import encrypt, decrypt


async def get_provider_config(
    db: aiosqlite.Connection,
    scope: str,
    scope_id: str,
    provider: str,
    environment: str | None = None,
) -> dict | None:
    """Get a single provider config by scope + provider + environment."""
    if environment is None:
        async with db.execute(
            "SELECT * FROM provider_configs WHERE scope = ? AND scope_id = ? AND provider = ? AND environment IS NULL",
            (scope, scope_id, provider),
        ) as cursor:
            row = await cursor.fetchone()
    else:
        async with db.execute(
            "SELECT * FROM provider_configs WHERE scope = ? AND scope_id = ? AND provider = ? AND environment = ?",
            (scope, scope_id, provider, environment),
        ) as cursor:
            row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_provider_configs(
    db: aiosqlite.Connection,
    scope: str,
    scope_id: str,
) -> list[dict]:
    """List all provider configs for a given scope."""
    async with db.execute(
        "SELECT * FROM provider_configs WHERE scope = ? AND scope_id = ? ORDER BY provider, environment",
        (scope, scope_id),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_dict(row) for row in rows]


async def upsert_provider_config(
    db: aiosqlite.Connection,
    scope: str,
    scope_id: str,
    provider: str,
    environment: str | None = None,
    config_json: dict | None = None,
    secrets: dict | None = None,
) -> str:
    """Insert or update a provider config. Returns the config id."""
    existing = await get_provider_config(db, scope, scope_id, provider, environment)

    config_str = json.dumps(config_json or {})
    secrets_enc = None
    if secrets:
        secrets_enc = encrypt(json.dumps(secrets))
    elif existing and existing.get("_secrets_encrypted_raw"):
        # Preserve existing secrets if none provided
        secrets_enc = existing["_secrets_encrypted_raw"]

    if existing:
        config_id = existing["id"]
        await db.execute(
            "UPDATE provider_configs SET config_json = ?, secrets_encrypted = ?, updated_at = datetime('now') WHERE id = ?",
            (config_str, secrets_enc, config_id),
        )
    else:
        config_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO provider_configs (id, scope, scope_id, provider, environment, config_json, secrets_encrypted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (config_id, scope, scope_id, provider, environment, config_str, secrets_enc),
        )
    await db.commit()
    return config_id


async def delete_provider_config(
    db: aiosqlite.Connection,
    scope: str,
    scope_id: str,
    provider: str,
    environment: str | None = None,
) -> bool:
    """Delete a provider config. Returns True if a row was deleted."""
    if environment is None:
        cursor = await db.execute(
            "DELETE FROM provider_configs WHERE scope = ? AND scope_id = ? AND provider = ? AND environment IS NULL",
            (scope, scope_id, provider),
        )
    else:
        cursor = await db.execute(
            "DELETE FROM provider_configs WHERE scope = ? AND scope_id = ? AND provider = ? AND environment = ?",
            (scope, scope_id, provider, environment),
        )
    await db.commit()
    return cursor.rowcount > 0


def _row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert a row to dict, decrypting secrets and masking them for safe output."""
    d = dict(row)
    # Store raw encrypted value for internal use (preserving on update)
    d["_secrets_encrypted_raw"] = d.get("secrets_encrypted")

    # Decrypt secrets for internal use
    secrets_enc = d.pop("secrets_encrypted", None)
    if secrets_enc:
        try:
            d["secrets"] = json.loads(decrypt(secrets_enc))
        except Exception:
            d["secrets"] = {}
    else:
        d["secrets"] = {}

    # Parse config_json
    if isinstance(d.get("config_json"), str):
        try:
            d["config_json"] = json.loads(d["config_json"])
        except (json.JSONDecodeError, TypeError):
            d["config_json"] = {}

    return d


def mask_secrets(config: dict) -> dict:
    """Return a copy with secrets masked for API responses."""
    result = {k: v for k, v in config.items() if not k.startswith("_")}
    secrets = result.get("secrets", {})
    masked = {}
    for key, value in secrets.items():
        if isinstance(value, str) and len(value) > 8:
            masked[key] = value[:4] + "..." + value[-4:]
        elif isinstance(value, str):
            masked[key] = "****"
        masked[f"has_{key}"] = bool(value)
    result["secrets"] = masked
    return result
