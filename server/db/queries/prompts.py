from __future__ import annotations

import json

import aiosqlite


async def get_prompt(db: aiosqlite.Connection, prompt_id: str) -> dict | None:
    async with db.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_prompt_by_name(
    db: aiosqlite.Connection,
    app_id: str,
    name: str,
    environment: str | None = None,
) -> dict | None:
    sql = "SELECT * FROM prompts WHERE app_id = ? AND name = ?"
    params: list = [app_id, name]
    if environment:
        sql += " AND environment = ?"
        params.append(environment)
    sql += " AND active = 1 LIMIT 1"
    async with db.execute(sql, params) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def find_app_by_org_and_repo(
    db: aiosqlite.Connection, org: str, app_name: str
) -> dict | None:
    """Find app by org github_owner and repo name (for public API lookups)."""
    sql = """
        SELECT a.* FROM applications a
        JOIN organizations o ON o.id = a.org_id
        WHERE o.github_owner = ? AND (a.github_repo = ? OR a.github_repo LIKE ?)
        LIMIT 1
    """
    full_repo = f"{org}/{app_name}"
    async with db.execute(sql, (org, full_repo, f"%/{app_name}")) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_prompts(
    db: aiosqlite.Connection,
    app_id: str,
    search: str | None = None,
    domain: str | None = None,
    prompt_type: str | None = None,
    environment: str | None = None,
    tags: list[str] | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    conditions = ["app_id = ?"]
    params: list = [app_id]

    if search:
        conditions.append("(name LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if domain:
        conditions.append("domain = ?")
        params.append(domain)
    if prompt_type:
        conditions.append("type = ?")
        params.append(prompt_type)
    if environment:
        conditions.append("environment = ?")
        params.append(environment)
    if active is not None:
        conditions.append("active = ?")
        params.append(1 if active else 0)
    if tags:
        for tag in tags:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

    where = " AND ".join(conditions)

    # Count
    async with db.execute(f"SELECT COUNT(*) FROM prompts WHERE {where}", params) as cursor:
        total = (await cursor.fetchone())[0]

    # Fetch
    sql = f"SELECT * FROM prompts WHERE {where} ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with db.execute(sql, params) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total


async def upsert_prompt(db: aiosqlite.Connection, data: dict) -> None:
    await db.execute(
        """INSERT INTO prompts
           (id, app_id, name, file_path, domain, description, type,
            modality_input, modality_output, default_model, environment,
            tags, active, version, git_sha, front_matter, body_hash,
            last_synced_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
           ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, file_path=excluded.file_path, domain=excluded.domain,
            description=excluded.description, type=excluded.type,
            modality_input=excluded.modality_input, modality_output=excluded.modality_output,
            default_model=excluded.default_model, environment=excluded.environment,
            tags=excluded.tags, active=excluded.active, version=excluded.version,
            git_sha=excluded.git_sha, front_matter=excluded.front_matter,
            body_hash=excluded.body_hash, last_synced_at=datetime('now'),
            updated_at=datetime('now')
        """,
        (
            data["id"], data["app_id"], data["name"], data["file_path"],
            data.get("domain"), data.get("description"), data.get("type", "chat"),
            data.get("modality_input", "text"), data.get("modality_output", "text"),
            data.get("default_model"), data.get("environment", "development"),
            data.get("tags", "[]"), 1 if data.get("active", True) else 0,
            data.get("version"), data.get("git_sha"), data.get("front_matter", "{}"),
            data.get("body_hash"),
        ),
    )
    await db.commit()


async def delete_prompt(db: aiosqlite.Connection, prompt_id: str) -> None:
    await db.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    await db.commit()


async def delete_prompts_by_app(db: aiosqlite.Connection, app_id: str) -> None:
    await db.execute("DELETE FROM prompts WHERE app_id = ?", (app_id,))
    await db.commit()


async def log_access(
    db: aiosqlite.Connection,
    prompt_id: str,
    prompt_name: str | None,
    api_key_id: str | None,
    version_served: str | None,
    cache_hit: bool,
    response_time_ms: int,
    client_ip: str | None,
    user_agent: str | None,
) -> None:
    await db.execute(
        """INSERT INTO prompt_access_log
           (prompt_id, prompt_name, api_key_id, version_served, cache_hit,
            response_time_ms, client_ip, user_agent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (prompt_id, prompt_name, api_key_id, version_served, 1 if cache_hit else 0,
         response_time_ms, client_ip, user_agent),
    )
    await db.commit()
