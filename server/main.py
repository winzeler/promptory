"""Promptdis — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.db.database import init_db, close_db, get_db
from server.auth.sessions import cleanup_expired_sessions
from server.auth.middleware import AuthMiddleware
from server.auth.rate_limiter import RateLimitMiddleware

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


async def _session_cleanup_loop():
    """Background task: clean up expired sessions every hour."""
    while True:
        await asyncio.sleep(3600)
        try:
            db = await get_db()
            deleted = await cleanup_expired_sessions(db)
            if deleted:
                logger.info("Session cleanup: removed %d expired sessions", deleted)
        except Exception:
            logger.exception("Session cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Promptdis server...")
    await init_db()

    cleanup_task = None
    if settings.deployment_mode != "lambda":
        # Container mode: run session cleanup loop in background
        cleanup_task = asyncio.create_task(_session_cleanup_loop())

    logger.info("Promptdis server ready (mode=%s)", settings.deployment_mode)
    yield

    if cleanup_task:
        cleanup_task.cancel()
    await close_db()
    logger.info("Promptdis server stopped")


app = FastAPI(
    title="Promptdis",
    description="Git-native LLM prompt management platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware order: Starlette LIFO — last added runs outermost (first).
# We want: request → RateLimiter → Auth → route handlers
# So add Auth first, then RateLimiter (RateLimiter becomes outermost).
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# Import and register routers
from server.auth.github_oauth import router as auth_router
from server.api.public import router as public_router
from server.api.admin import router as admin_router
from server.api.webhooks import router as webhooks_router
from server.api.api_keys import router as api_keys_router
from server.api.eval import router as eval_router

app.include_router(auth_router)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(api_keys_router)
app.include_router(eval_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "promptdis", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"service": "promptdis", "docs": "/docs"}
