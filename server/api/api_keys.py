"""API key management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from server.db.database import get_db
from server.db.queries import api_keys as key_queries
from server.auth.api_keys import generate_api_key

router = APIRouter(prefix="/api/v1/admin/api-keys", tags=["api-keys"])


def _require_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}})
    return user


@router.get("")
async def list_api_keys(request: Request):
    user = _require_user(request)
    db = await get_db()
    keys = await key_queries.list_keys_for_user(db, user["id"])

    # Parse scopes JSON
    for key in keys:
        if isinstance(key.get("scopes"), str):
            try:
                key["scopes"] = json.loads(key["scopes"])
            except (json.JSONDecodeError, TypeError):
                key["scopes"] = None

    return {"items": keys}


@router.post("")
async def create_api_key(request: Request):
    user = _require_user(request)
    db = await get_db()
    body = await request.json()

    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": "name is required"}})

    scopes = body.get("scopes")
    scopes_json = json.dumps(scopes) if scopes else None
    expires_at = body.get("expires_at")

    full_key, key_hash, key_prefix = generate_api_key()

    key_id = await key_queries.create_key(
        db, user["id"], key_hash, key_prefix, name,
        scopes=scopes_json, expires_at=expires_at,
    )

    return {
        "id": key_id,
        "key": full_key,  # Shown only once!
        "key_prefix": key_prefix,
        "name": name,
        "scopes": scopes,
        "expires_at": expires_at,
    }


@router.delete("/{key_id}")
async def revoke_api_key(key_id: str, request: Request):
    user = _require_user(request)
    db = await get_db()
    success = await key_queries.revoke_key(db, key_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "API key not found"}})
    return {"ok": True}
