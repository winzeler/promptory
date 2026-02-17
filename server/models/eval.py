from __future__ import annotations

from pydantic import BaseModel


class EvalRunCreate(BaseModel):
    models: list[str] = []
    dataset: str | None = None


class EvalRun(BaseModel):
    id: str
    prompt_id: str
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None
    status: str = "pending"
    results: dict | None = None
    error_message: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    triggered_by: str = "manual"
    created_at: str | None = None
