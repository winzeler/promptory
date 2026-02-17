from __future__ import annotations

import uuid

import aiosqlite


async def list_orgs(db: aiosqlite.Connection) -> list[dict]:
    async with db.execute("SELECT * FROM organizations ORDER BY display_name") as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def list_orgs_for_user(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    sql = """
        SELECT o.* FROM organizations o
        JOIN org_memberships om ON om.org_id = o.id
        WHERE om.user_id = ?
        ORDER BY o.display_name
    """
    async with db.execute(sql, (user_id,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_org(db: aiosqlite.Connection, org_id: str) -> dict | None:
    async with db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_org_by_owner(db: aiosqlite.Connection, github_owner: str) -> dict | None:
    async with db.execute(
        "SELECT * FROM organizations WHERE github_owner = ?", (github_owner,)
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def upsert_org(
    db: aiosqlite.Connection,
    github_owner: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> str:
    existing = await get_org_by_owner(db, github_owner)
    if existing:
        await db.execute(
            "UPDATE organizations SET display_name=?, avatar_url=?, updated_at=datetime('now') WHERE id=?",
            (display_name or existing["display_name"], avatar_url, existing["id"]),
        )
        await db.commit()
        return existing["id"]

    org_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO organizations (id, github_owner, display_name, avatar_url) VALUES (?, ?, ?, ?)",
        (org_id, github_owner, display_name or github_owner, avatar_url),
    )
    await db.commit()
    return org_id
