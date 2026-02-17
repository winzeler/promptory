from __future__ import annotations

import uuid

import aiosqlite


async def list_keys_for_user(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    async with db.execute(
        "SELECT id, key_prefix, name, scopes, expires_at, revoked_at, last_used_at, created_at "
        "FROM api_keys WHERE user_id = ? AND revoked_at IS NULL ORDER BY created_at DESC",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_key_by_hash(db: aiosqlite.Connection, key_hash: str) -> dict | None:
    async with db.execute(
        "SELECT * FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL", (key_hash,)
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_key_by_prefix(db: aiosqlite.Connection, prefix: str) -> list[dict]:
    async with db.execute(
        "SELECT * FROM api_keys WHERE key_prefix = ? AND revoked_at IS NULL", (prefix,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def create_key(
    db: aiosqlite.Connection,
    user_id: str,
    key_hash: str,
    key_prefix: str,
    name: str,
    scopes: str | None = None,
    expires_at: str | None = None,
) -> str:
    key_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, scopes, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (key_id, user_id, key_hash, key_prefix, name, scopes, expires_at),
    )
    await db.commit()
    return key_id


async def revoke_key(db: aiosqlite.Connection, key_id: str, user_id: str) -> bool:
    result = await db.execute(
        "UPDATE api_keys SET revoked_at = datetime('now') WHERE id = ? AND user_id = ?",
        (key_id, user_id),
    )
    await db.commit()
    return result.rowcount > 0


async def update_last_used(db: aiosqlite.Connection, key_id: str) -> None:
    await db.execute(
        "UPDATE api_keys SET last_used_at = datetime('now') WHERE id = ?", (key_id,)
    )
    await db.commit()
