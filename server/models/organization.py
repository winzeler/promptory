from __future__ import annotations

from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    github_owner: str
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: str | None = None


class Application(BaseModel):
    id: str
    org_id: str
    github_repo: str
    subdirectory: str = ""
    display_name: str | None = None
    default_branch: str = "main"
    webhook_secret: str | None = None
    last_synced_at: str | None = None
    created_at: str | None = None


class AppCreate(BaseModel):
    github_repo: str
    subdirectory: str = ""
    display_name: str | None = None
    default_branch: str = "main"


class AppUpdate(BaseModel):
    display_name: str | None = None
    default_branch: str | None = None
    subdirectory: str | None = None
