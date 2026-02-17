from __future__ import annotations

import secrets
import uuid

import aiosqlite


async def list_apps_for_org(db: aiosqlite.Connection, org_id: str) -> list[dict]:
    async with db.execute(
        "SELECT * FROM applications WHERE org_id = ? ORDER BY display_name", (org_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_app(db: aiosqlite.Connection, app_id: str) -> dict | None:
    async with db.execute("SELECT * FROM applications WHERE id = ?", (app_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_app_by_repo(
    db: aiosqlite.Connection, org_id: str, github_repo: str, subdirectory: str = ""
) -> dict | None:
    async with db.execute(
        "SELECT * FROM applications WHERE org_id = ? AND github_repo = ? AND subdirectory = ?",
        (org_id, github_repo, subdirectory),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_app(
    db: aiosqlite.Connection,
    org_id: str,
    github_repo: str,
    subdirectory: str = "",
    display_name: str | None = None,
    default_branch: str = "main",
) -> str:
    app_id = str(uuid.uuid4())
    webhook_secret = secrets.token_hex(32)
    await db.execute(
        """INSERT INTO applications
           (id, org_id, github_repo, subdirectory, display_name, default_branch, webhook_secret)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (app_id, org_id, github_repo, subdirectory, display_name or github_repo, default_branch, webhook_secret),
    )
    await db.commit()
    return app_id


async def update_app(
    db: aiosqlite.Connection,
    app_id: str,
    display_name: str | None = None,
    default_branch: str | None = None,
    subdirectory: str | None = None,
) -> None:
    updates = []
    params = []
    if display_name is not None:
        updates.append("display_name = ?")
        params.append(display_name)
    if default_branch is not None:
        updates.append("default_branch = ?")
        params.append(default_branch)
    if subdirectory is not None:
        updates.append("subdirectory = ?")
        params.append(subdirectory)
    if not updates:
        return
    updates.append("updated_at = datetime('now')")
    params.append(app_id)
    await db.execute(f"UPDATE applications SET {', '.join(updates)} WHERE id = ?", params)
    await db.commit()


async def delete_app(db: aiosqlite.Connection, app_id: str) -> None:
    await db.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    await db.commit()


async def update_sync_time(db: aiosqlite.Connection, app_id: str) -> None:
    await db.execute(
        "UPDATE applications SET last_synced_at = datetime('now') WHERE id = ?", (app_id,)
    )
    await db.commit()
