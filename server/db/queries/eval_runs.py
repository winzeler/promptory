from __future__ import annotations

import uuid

import aiosqlite


async def create_eval_run(
    db: aiosqlite.Connection,
    prompt_id: str,
    prompt_version: str | None,
    provider: str,
    model: str,
    triggered_by: str = "manual",
) -> str:
    run_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO eval_runs (id, prompt_id, prompt_version, provider, model, triggered_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (run_id, prompt_id, prompt_version, provider, model, triggered_by),
    )
    await db.commit()
    return run_id


async def update_eval_run(
    db: aiosqlite.Connection,
    run_id: str,
    status: str,
    results: str | None = None,
    error_message: str | None = None,
    cost_usd: float | None = None,
    duration_ms: int | None = None,
) -> None:
    await db.execute(
        """UPDATE eval_runs
           SET status=?, results=?, error_message=?, cost_usd=?, duration_ms=?
           WHERE id=?""",
        (status, results, error_message, cost_usd, duration_ms, run_id),
    )
    await db.commit()


async def list_eval_runs(
    db: aiosqlite.Connection, prompt_id: str, limit: int = 20
) -> list[dict]:
    async with db.execute(
        "SELECT * FROM eval_runs WHERE prompt_id = ? ORDER BY created_at DESC LIMIT ?",
        (prompt_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_eval_run(db: aiosqlite.Connection, run_id: str) -> dict | None:
    async with db.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_eval_run(db: aiosqlite.Connection, run_id: str) -> None:
    await db.execute("DELETE FROM eval_runs WHERE id = ?", (run_id,))
    await db.commit()
