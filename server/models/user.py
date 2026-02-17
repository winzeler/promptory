from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    id: str
    github_id: int
    github_login: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False
    created_at: str | None = None
    last_login_at: str | None = None


class Session(BaseModel):
    id: str
    user_id: str
    expires_at: str
    created_at: str | None = None
