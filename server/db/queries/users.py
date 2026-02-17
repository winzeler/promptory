from __future__ import annotations

import uuid

import aiosqlite


async def get_user(db: aiosqlite.Connection, user_id: str) -> dict | None:
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_github_id(db: aiosqlite.Connection, github_id: int) -> dict | None:
    async with db.execute(
        "SELECT * FROM users WHERE github_id = ?", (github_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def upsert_user(
    db: aiosqlite.Connection,
    github_id: int,
    github_login: str,
    display_name: str | None = None,
    email: str | None = None,
    avatar_url: str | None = None,
    access_token_encrypted: str | None = None,
) -> str:
    existing = await get_user_by_github_id(db, github_id)
    if existing:
        await db.execute(
            """UPDATE users SET github_login=?, display_name=?, email=?,
               avatar_url=?, access_token_encrypted=?, last_login_at=datetime('now')
               WHERE id=?""",
            (github_login, display_name, email, avatar_url, access_token_encrypted, existing["id"]),
        )
        await db.commit()
        return existing["id"]

    user_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO users
           (id, github_id, github_login, display_name, email, avatar_url,
            access_token_encrypted, last_login_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (user_id, github_id, github_login, display_name, email, avatar_url, access_token_encrypted),
    )
    await db.commit()
    return user_id


async def upsert_org_membership(
    db: aiosqlite.Connection, user_id: str, org_id: str, role: str = "member"
) -> None:
    await db.execute(
        """INSERT INTO org_memberships (user_id, org_id, role)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, org_id) DO UPDATE SET role=excluded.role""",
        (user_id, org_id, role),
    )
    await db.commit()
