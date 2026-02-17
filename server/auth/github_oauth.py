"""GitHub OAuth flow for web app authentication."""

from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from server.config import settings
from server.db.database import get_db
from server.db.queries import users as user_queries
from server.db.queries import organizations as org_queries
from server.utils.crypto import encrypt

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-memory CSRF state store (use Redis in production)
_oauth_states: dict[str, bool] = {}

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_ORGS_URL = "https://api.github.com/user/orgs"


@router.get("/github/login")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = True

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/v1/auth/github/callback",
        "scope": "repo read:user read:org",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{query}")


@router.get("/github/callback")
async def github_callback(code: str, state: str, response: Response):
    """Handle GitHub OAuth callback."""
    # Verify state
    if state not in _oauth_states:
        return RedirectResponse(f"{settings.frontend_url}/login?error=invalid_state")
    del _oauth_states[state]

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(f"{settings.frontend_url}/login?error=token_failed")

    # Fetch user profile
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        user_resp = await client.get(GITHUB_USER_URL, headers=headers)
        github_user = user_resp.json()

        # Fetch user's orgs
        orgs_resp = await client.get(GITHUB_ORGS_URL, headers=headers)
        github_orgs = orgs_resp.json() if orgs_resp.status_code == 200 else []

    db = await get_db()

    # Upsert user
    encrypted_token = encrypt(access_token)
    user_id = await user_queries.upsert_user(
        db,
        github_id=github_user["id"],
        github_login=github_user["login"],
        display_name=github_user.get("name"),
        email=github_user.get("email"),
        avatar_url=github_user.get("avatar_url"),
        access_token_encrypted=encrypted_token,
    )

    # Sync orgs
    for gh_org in github_orgs:
        org_id = await org_queries.upsert_org(
            db,
            github_owner=gh_org["login"],
            display_name=gh_org.get("login"),
            avatar_url=gh_org.get("avatar_url"),
        )
        await user_queries.upsert_org_membership(db, user_id, org_id, role="member")

    # Also ensure user's personal account is an org
    personal_org_id = await org_queries.upsert_org(
        db,
        github_owner=github_user["login"],
        display_name=github_user.get("name") or github_user["login"],
        avatar_url=github_user.get("avatar_url"),
    )
    await user_queries.upsert_org_membership(db, user_id, personal_org_id, role="admin")

    # Create session
    from server.auth.sessions import create_session

    session_id = await create_session(db, user_id)

    # Redirect to frontend with session cookie
    redirect = RedirectResponse(f"{settings.frontend_url}/", status_code=302)
    redirect.set_cookie(
        key="promptory_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
        secure=not settings.app_base_url.startswith("http://localhost"),
    )
    return redirect


@router.get("/me")
async def get_current_user(request: Request):
    """Get the currently authenticated user."""
    user = getattr(request.state, "user", None)
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": user["id"],
            "github_login": user["github_login"],
            "display_name": user["display_name"],
            "email": user["email"],
            "avatar_url": user["avatar_url"],
            "is_admin": bool(user.get("is_admin")),
        }
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Clear the session cookie."""
    session_id = request.cookies.get("promptory_session")
    if session_id:
        db = await get_db()
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    response.delete_cookie("promptory_session")
    return {"ok": True}
