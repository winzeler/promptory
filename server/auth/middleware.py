"""Authentication middleware for FastAPI."""

from __future__ import annotations

import logging

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from server.db.database import get_db
from server.auth.sessions import verify_session
from server.auth.api_keys import validate_api_key, parse_scopes

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/v1/auth/github/login",
    "/api/v1/auth/github/callback",
    "/api/v1/webhooks/github",
    "/health",
    "/",
}

# Paths that accept API key auth (public prompt fetching)
API_KEY_PATHS_PREFIX = "/api/v1/prompts"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # Initialize state
        request.state.user = None
        request.state.api_key = None

        try:
            db = await get_db()
        except RuntimeError:
            return await call_next(request)

        # Try session cookie auth first
        session_id = request.cookies.get("promptory_session")
        if session_id:
            user = await verify_session(db, session_id)
            if user:
                request.state.user = user
                return await call_next(request)

        # Try API key auth (Bearer token)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:].startswith("pm_"):
            api_key_record = await validate_api_key(db, auth_header[7:])
            if api_key_record:
                request.state.api_key = api_key_record
                request.state.api_key_scopes = parse_scopes(api_key_record.get("scopes"))
                return await call_next(request)

        # For public prompt API paths, require auth
        if path.startswith(API_KEY_PATHS_PREFIX):
            raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Valid API key required"}})

        # For admin paths, require session auth
        if path.startswith("/api/v1/admin"):
            raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Authentication required. Please sign in with GitHub."}})

        return await call_next(request)
