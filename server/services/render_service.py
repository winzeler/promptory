"""Jinja2 template rendering with sandboxed environment."""

from __future__ import annotations

import logging
import re

from jinja2 import BaseLoader
from jinja2.loaders import DictLoader
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

# Sandboxed environment prevents template injection attacks
_env = SandboxedEnvironment(
    loader=BaseLoader(),
    autoescape=False,
    keep_trailing_newline=True,
)


def render_prompt(template_body: str, variables: dict) -> str:
    """Render a Jinja2 template with the given variables.

    Uses a sandboxed environment to prevent template injection.
    Only variable substitution and safe filters are allowed.
    """
    try:
        template = _env.from_string(template_body)
        return template.render(**variables)
    except Exception as e:
        logger.error("Template rendering failed: %s", e)
        raise ValueError(f"Template rendering failed: {e}")


# ---------------------------------------------------------------------------
# Include-aware rendering (Prompt Composition)
# ---------------------------------------------------------------------------

_MAX_INCLUDE_DEPTH = 5

_INCLUDE_RE = re.compile(r'\{%[-\s]*include\s+["\']([^"\']+)["\']')


async def _resolve_includes(
    template_body: str,
    db,
    app_id: str,
    resolved: dict[str, str],
    seen: set[str],
    depth: int,
) -> None:
    """Recursively resolve all {% include "name" %} references from the DB."""
    import json

    for name in _INCLUDE_RE.findall(template_body):
        if depth >= _MAX_INCLUDE_DEPTH:
            raise ValueError(
                f"Include depth exceeded maximum of {_MAX_INCLUDE_DEPTH}"
            )

        if name in seen:
            raise ValueError(
                f"Circular include detected: '{name}' already included"
            )

        if name in resolved:
            continue

        async with db.execute(
            "SELECT front_matter FROM prompts WHERE app_id = ? AND name = ? AND active = 1 LIMIT 1",
            (app_id, name),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise ValueError(f"Include not found: '{name}'")

        fm = json.loads(row["front_matter"] or "{}")
        body = fm.get("_body", "")
        resolved[name] = body

        await _resolve_includes(body, db, app_id, resolved, seen | {name}, depth + 1)


async def render_prompt_with_includes(
    template_body: str,
    variables: dict,
    db,
    app_id: str,
) -> str:
    """Render a template that may contain {% include "prompt_name" %} directives.

    Includes are resolved from the prompts table within the same application.
    """
    resolved: dict[str, str] = {}
    await _resolve_includes(template_body, db, app_id, resolved, set(), 0)

    loader = DictLoader(resolved)
    env = SandboxedEnvironment(
        loader=loader,
        autoescape=False,
        keep_trailing_newline=True,
    )
    try:
        template = env.from_string(template_body)
        return template.render(**variables)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Template rendering with includes failed: %s", e)
        raise ValueError(f"Template rendering failed: {e}")
