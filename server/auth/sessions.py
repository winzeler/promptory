"""Server-side session management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import aiosqlite


SESSION_TTL_HOURS = 24


async def create_session(db: aiosqlite.Connection, user_id: str) -> str:
    """Create a new session and return the session ID."""
    session_id = secrets.token_urlsafe(48)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    await db.execute(
        "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
        (session_id, user_id, expires_at),
    )
    await db.commit()
    return session_id


async def verify_session(db: aiosqlite.Connection, session_id: str) -> dict | None:
    """Verify a session and return the associated user, or None if invalid/expired."""
    async with db.execute(
        """SELECT u.* FROM sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.id = ? AND s.expires_at > datetime('now')""",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            # Refresh session expiry on activity
            new_expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
            await db.execute(
                "UPDATE sessions SET expires_at = ? WHERE id = ?",
                (new_expires, session_id),
            )
            await db.commit()
            return dict(row)
    return None


async def cleanup_expired_sessions(db: aiosqlite.Connection) -> int:
    """Delete expired sessions. Returns count deleted."""
    result = await db.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
    await db.commit()
    return result.rowcount
