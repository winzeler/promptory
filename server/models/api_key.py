from __future__ import annotations

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    scopes: dict | None = None
    expires_at: str | None = None


class ApiKeyResponse(BaseModel):
    id: str
    key_prefix: str
    name: str
    scopes: dict | None = None
    expires_at: str | None = None
    last_used_at: str | None = None
    created_at: str | None = None


class ApiKeyCreated(ApiKeyResponse):
    """Returned only on creation — includes the full key (shown once)."""
    key: str
