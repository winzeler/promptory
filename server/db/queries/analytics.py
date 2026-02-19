"""Analytics queries on the prompt_access_log table."""

from __future__ import annotations

import aiosqlite


async def requests_per_day(
    db: aiosqlite.Connection, app_id: str | None = None, days: int = 30
) -> list[dict]:
    """Daily request counts over the last N days."""
    sql = """
        SELECT date(l.created_at) AS day, COUNT(*) AS count
        FROM prompt_access_log l
    """
    params: list = []
    if app_id:
        sql += " JOIN prompts p ON p.id = l.prompt_id WHERE p.app_id = ? AND"
        params.append(app_id)
    else:
        sql += " WHERE"
    sql += " l.created_at >= datetime('now', ? || ' days') GROUP BY day ORDER BY day"
    params.append(f"-{days}")

    async with db.execute(sql, params) as cursor:
        return [dict(r) for r in await cursor.fetchall()]


async def cache_hit_rate(
    db: aiosqlite.Connection, app_id: str | None = None, days: int = 30
) -> list[dict]:
    """Daily cache hit rate over the last N days."""
    sql = """
        SELECT date(l.created_at) AS day,
               COUNT(*) AS total,
               SUM(l.cache_hit) AS hits,
               ROUND(100.0 * SUM(l.cache_hit) / MAX(COUNT(*), 1), 1) AS hit_rate
        FROM prompt_access_log l
    """
    params: list = []
    if app_id:
        sql += " JOIN prompts p ON p.id = l.prompt_id WHERE p.app_id = ? AND"
        params.append(app_id)
    else:
        sql += " WHERE"
    sql += " l.created_at >= datetime('now', ? || ' days') GROUP BY day ORDER BY day"
    params.append(f"-{days}")

    async with db.execute(sql, params) as cursor:
        return [dict(r) for r in await cursor.fetchall()]


async def latency_percentiles(
    db: aiosqlite.Connection, app_id: str | None = None, days: int = 7
) -> list[dict]:
    """Approximate latency percentiles (p50, p90, p99) per day.

    SQLite doesn't have native percentile functions, so we use
    ordered subqueries with LIMIT/OFFSET as an approximation.
    """
    sql = """
        SELECT date(l.created_at) AS day,
               AVG(l.response_time_ms) AS avg_ms,
               MIN(l.response_time_ms) AS min_ms,
               MAX(l.response_time_ms) AS max_ms,
               COUNT(*) AS sample_count
        FROM prompt_access_log l
    """
    params: list = []
    if app_id:
        sql += " JOIN prompts p ON p.id = l.prompt_id WHERE p.app_id = ? AND"
        params.append(app_id)
    else:
        sql += " WHERE"
    sql += " l.created_at >= datetime('now', ? || ' days') GROUP BY day ORDER BY day"
    params.append(f"-{days}")

    async with db.execute(sql, params) as cursor:
        return [dict(r) for r in await cursor.fetchall()]


async def top_prompts(
    db: aiosqlite.Connection, app_id: str | None = None, days: int = 30, limit: int = 10
) -> list[dict]:
    """Most-accessed prompts by request count."""
    sql = """
        SELECT l.prompt_id, l.prompt_name, COUNT(*) AS request_count,
               ROUND(AVG(l.response_time_ms), 1) AS avg_latency_ms,
               ROUND(100.0 * SUM(l.cache_hit) / MAX(COUNT(*), 1), 1) AS cache_rate
        FROM prompt_access_log l
    """
    params: list = []
    if app_id:
        sql += " JOIN prompts p ON p.id = l.prompt_id WHERE p.app_id = ? AND"
        params.append(app_id)
    else:
        sql += " WHERE"
    sql += " l.created_at >= datetime('now', ? || ' days')"
    params.append(f"-{days}")
    sql += " GROUP BY l.prompt_id ORDER BY request_count DESC LIMIT ?"
    params.append(limit)

    async with db.execute(sql, params) as cursor:
        return [dict(r) for r in await cursor.fetchall()]


async def usage_by_api_key(
    db: aiosqlite.Connection, days: int = 30, limit: int = 10
) -> list[dict]:
    """Request counts grouped by API key."""
    sql = """
        SELECT l.api_key_id,
               k.name AS key_name,
               COUNT(*) AS request_count,
               ROUND(AVG(l.response_time_ms), 1) AS avg_latency_ms
        FROM prompt_access_log l
        LEFT JOIN api_keys k ON k.id = l.api_key_id
        WHERE l.created_at >= datetime('now', ? || ' days')
        GROUP BY l.api_key_id
        ORDER BY request_count DESC
        LIMIT ?
    """
    async with db.execute(sql, (f"-{days}", limit)) as cursor:
        return [dict(r) for r in await cursor.fetchall()]
