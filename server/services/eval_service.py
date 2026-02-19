"""Promptfoo evaluation service — config generation and subprocess execution."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

import aiosqlite

from server.db.queries import eval_runs as eval_queries

logger = logging.getLogger(__name__)


def generate_promptfoo_config(
    prompt_body: str,
    models: list[str],
    eval_config: dict | None = None,
    variables: dict | None = None,
) -> dict:
    """Generate a promptfooconfig dict from prompt metadata.

    Args:
        prompt_body: The raw Jinja2 template body.
        models: List of model identifiers (e.g. ["gemini-2.0-flash", "gpt-4o"]).
        eval_config: The prompt's `eval` front-matter section (assertions, dataset).
        variables: Sample variables for test cases.

    Returns:
        A dict suitable for YAML serialization as promptfooconfig.yaml.
    """
    eval_config = eval_config or {}
    variables = variables or {}

    # Map model strings to promptfoo provider format
    providers = []
    for model in models:
        if "gemini" in model.lower() or "google" in model.lower():
            providers.append(f"google:{model}")
        elif "gpt" in model.lower() or "openai" in model.lower():
            providers.append(f"openai:{model}")
        elif "claude" in model.lower() or "anthropic" in model.lower():
            providers.append(f"anthropic:{model}")
        else:
            providers.append(model)

    # Build assertions from eval config
    assertions = []
    for assertion in eval_config.get("assertions", []):
        a = {"type": assertion["type"], "value": assertion["value"]}
        if "threshold" in assertion:
            a["threshold"] = assertion["threshold"]
        assertions.append(a)

    # Build test case
    test_case: dict = {}
    if variables:
        test_case["vars"] = variables
    if assertions:
        test_case["assert"] = assertions

    config: dict = {
        "prompts": [prompt_body],
        "providers": providers,
    }

    if test_case:
        config["tests"] = [test_case]

    return config


async def run_evaluation(
    db: aiosqlite.Connection,
    run_id: str,
    prompt_body: str,
    model: str,
    eval_config: dict | None = None,
    variables: dict | None = None,
) -> dict:
    """Run a promptfoo evaluation for a single model.

    Creates a temporary config file, runs promptfoo as a subprocess,
    parses results, and updates the eval_run record.

    Returns the parsed results dict.
    """
    start_time = time.time()

    # Check that promptfoo is installed
    promptfoo_bin = shutil.which("promptfoo")
    if not promptfoo_bin:
        error_msg = "promptfoo CLI not found. Install with: npm install -g promptfoo"
        await eval_queries.update_eval_run(
            db, run_id,
            status="failed",
            error_message=error_msg,
        )
        return {"error": error_msg, "status": "failed"}

    # Mark as running
    await eval_queries.update_eval_run(db, run_id, status="running")

    config = generate_promptfoo_config(prompt_body, [model], eval_config, variables)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "promptfooconfig.yaml"
        output_path = Path(tmpdir) / "output.json"

        # Write config as YAML
        import yaml
        config_path.write_text(yaml.dump(config, default_flow_style=False))

        try:
            proc = await asyncio.create_subprocess_exec(
                promptfoo_bin, "eval",
                "--config", str(config_path),
                "--output", str(output_path),
                "--no-cache",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            duration_ms = int((time.time() - start_time) * 1000)

            if output_path.exists():
                raw = output_path.read_text()
                try:
                    results = json.loads(raw)
                except json.JSONDecodeError:
                    results = {"raw_output": raw[:5000]}
            else:
                results = {
                    "stdout": stdout.decode(errors="replace")[:5000],
                    "stderr": stderr.decode(errors="replace")[:5000],
                    "exit_code": proc.returncode,
                }

            # Extract cost if available
            cost_usd = None
            if isinstance(results, dict) and "results" in results:
                total_cost = sum(
                    r.get("cost", 0) or 0
                    for r in results.get("results", [])
                    if isinstance(r, dict)
                )
                if total_cost > 0:
                    cost_usd = total_cost

            status = "completed" if proc.returncode == 0 else "failed"
            error_msg = None
            if proc.returncode != 0:
                error_msg = stderr.decode(errors="replace")[:2000]

            await eval_queries.update_eval_run(
                db, run_id,
                status=status,
                results=json.dumps(results),
                error_message=error_msg,
                cost_usd=cost_usd,
                duration_ms=duration_ms,
            )

            return {"status": status, "results": results, "duration_ms": duration_ms}

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            await eval_queries.update_eval_run(
                db, run_id,
                status="failed",
                error_message="Evaluation timed out after 120 seconds",
                duration_ms=duration_ms,
            )
            return {"status": "failed", "error": "Evaluation timed out"}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception("Eval run %s failed", run_id)
            await eval_queries.update_eval_run(
                db, run_id,
                status="failed",
                error_message=str(e)[:2000],
                duration_ms=duration_ms,
            )
            return {"status": "failed", "error": str(e)}
