"""Sliding-window rate limiter middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from server.config import settings

SKIP_PATHS = {"/health", "/docs", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter.

    Key is the API key prefix (if present) or client IP.
    """

    def __init__(self, app, limit: int | None = None):
        super().__init__(app)
        self.limit = limit or settings.rate_limit_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in SKIP_PATHS or path.startswith("/docs"):
            return await call_next(request)

        key = self._get_key(request)
        now = time.monotonic()
        window = self._windows[key]

        # Prune timestamps older than 60 seconds
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.pop(0)

        if len(window) >= self.limit:
            retry_after = int(60 - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many requests"}},
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        return await call_next(request)

    @staticmethod
    def _get_key(request: Request) -> str:
        api_key = getattr(request.state, "api_key", None)
        if api_key and isinstance(api_key, dict):
            return f"key:{api_key.get('key_prefix', 'unknown')}"
        return f"ip:{request.client.host if request.client else 'unknown'}"
