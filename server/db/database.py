import logging
import os
from pathlib import Path

import aiosqlite

from server.config import settings

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def init_db() -> None:
    global _db
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(db_path))
    _db.row_factory = aiosqlite.Row

    if settings.deployment_mode == "lambda":
        # EFS lacks mmap support required for WAL; use DELETE journal mode
        await _db.execute("PRAGMA journal_mode=DELETE")
        await _db.execute("PRAGMA busy_timeout=5000")
    else:
        await _db.execute("PRAGMA journal_mode=WAL")

    await _db.execute("PRAGMA foreign_keys=ON")

    await _run_migrations(_db)
    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


async def _run_migrations(db: aiosqlite.Connection) -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return

    # Check current version
    try:
        async with db.execute("SELECT MAX(version) FROM schema_version") as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0
    except aiosqlite.OperationalError:
        current_version = 0

    # Find and apply pending migrations
    migration_files = sorted(migrations_dir.glob("*.sql"))
    for mf in migration_files:
        version = int(mf.stem.split("_")[0])
        if version > current_version:
            logger.info("Applying migration %s", mf.name)
            sql = mf.read_text()
            await db.executescript(sql)
            await db.commit()

    logger.info("Migrations complete (at version %d)", current_version)
