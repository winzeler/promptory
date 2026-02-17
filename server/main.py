"""Promptory — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.db.database import init_db, close_db
from server.auth.middleware import AuthMiddleware

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Promptory server...")
    await init_db()
    logger.info("Promptory server ready")
    yield
    await close_db()
    logger.info("Promptory server stopped")


app = FastAPI(
    title="Promptory",
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

# Auth middleware
app.add_middleware(AuthMiddleware)

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
    return {"status": "ok", "service": "promptory", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"service": "promptory", "docs": "/docs"}
