"""Evaluation API endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from server.db.database import get_db
from server.db.queries import prompts as prompt_queries
from server.db.queries import eval_runs as eval_queries
from server.services.eval_service import run_evaluation

router = APIRouter(prefix="/api/v1/admin", tags=["eval"])


def _require_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}})
    return user


@router.post("/prompts/{prompt_id}/eval")
async def run_eval(prompt_id: str, request: Request):
    """Run an evaluation for a prompt against one or more models."""
    _require_user(request)
    db = await get_db()
    body = await request.json()

    prompt = await prompt_queries.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"}})

    models = body.get("models", ["gemini-2.0-flash"])
    variables = body.get("variables")

    # Extract eval config and body from front-matter
    fm = json.loads(prompt.get("front_matter", "{}"))
    eval_config = fm.get("eval")
    prompt_body = fm.get("_body", "")

    # Create eval run records
    runs = []
    for model in models:
        run_id = await eval_queries.create_eval_run(
            db, prompt_id,
            prompt_version=prompt.get("version"),
            provider="promptfoo",
            model=model,
            triggered_by="manual",
        )
        runs.append({"id": run_id, "model": model, "status": "pending"})

    # Fire evaluations in the background so the API returns immediately
    async def _run_all():
        for run_info in runs:
            await run_evaluation(
                db, run_info["id"], prompt_body, run_info["model"],
                eval_config=eval_config, variables=variables,
            )

    asyncio.create_task(_run_all())

    return {"runs": runs, "message": "Evaluation started. Poll GET /eval/runs/{id} for results."}


@router.get("/prompts/{prompt_id}/eval/runs")
async def list_eval_runs(prompt_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    runs = await eval_queries.list_eval_runs(db, prompt_id)

    for run in runs:
        if isinstance(run.get("results"), str):
            try:
                run["results"] = json.loads(run["results"])
            except (json.JSONDecodeError, TypeError):
                pass

    return {"items": runs}


@router.get("/eval/runs/{run_id}")
async def get_eval_run(run_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    run = await eval_queries.get_eval_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Eval run not found"}})

    if isinstance(run.get("results"), str):
        try:
            run["results"] = json.loads(run["results"])
        except (json.JSONDecodeError, TypeError):
            pass

    return run


@router.delete("/eval/runs/{run_id}")
async def delete_eval_run(run_id: str, request: Request):
    _require_user(request)
    db = await get_db()
    await eval_queries.delete_eval_run(db, run_id)
    return {"ok": True}
