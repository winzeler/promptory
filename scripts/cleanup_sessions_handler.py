"""EventBridge-triggered Lambda handler — cleans up expired Promptdis sessions.

Replaces the `_session_cleanup_loop()` asyncio background task used in
container mode. Scheduled via EventBridge at rate(1 hour).
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def _cleanup() -> int:
    from server.db.database import init_db, get_db, close_db

    await init_db()
    try:
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE expires_at <= datetime('now')"
        )
        await db.commit()
        deleted = cursor.rowcount
        logger.info("Session cleanup: removed %d expired sessions", deleted)
        return deleted
    finally:
        await close_db()


def handler(event: dict, context: object) -> dict:
    """Lambda entry point."""
    deleted = asyncio.get_event_loop().run_until_complete(_cleanup())
    return {"statusCode": 200, "body": f"Cleaned up {deleted} expired sessions"}
