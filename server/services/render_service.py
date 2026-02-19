"""Jinja2 template rendering with sandboxed environment."""

from __future__ import annotations

import logging

from jinja2 import BaseLoader
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


class PromptIncludeLoader(BaseLoader):
    """Jinja2 loader that resolves {% include "name" %} from the prompt DB.

    Looks up prompts by *name* within the same application. Enforces max
    depth and circular-reference detection.
    """

    def __init__(self, db, app_id: str):
        self._db = db
        self._app_id = app_id
        self._seen: set[str] = set()
        self._depth = 0

    def get_source(self, environment, template):
        import asyncio

        if self._depth >= _MAX_INCLUDE_DEPTH:
            raise ValueError(
                f"Include depth exceeded maximum of {_MAX_INCLUDE_DEPTH}"
            )

        if template in self._seen:
            raise ValueError(
                f"Circular include detected: '{template}' already included"
            )

        self._seen.add(template)
        self._depth += 1

        try:
            source = asyncio.get_event_loop().run_until_complete(
                self._load(template)
            )
        except RuntimeError:
            # If we're inside an async context, use a synchronous fallback
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                source = pool.submit(
                    asyncio.run, self._load(template)
                ).result()

        return source, template, lambda: False

    async def _load(self, name: str) -> str:
        import json
        async with self._db.execute(
            "SELECT front_matter FROM prompts WHERE app_id = ? AND name = ? AND active = 1 LIMIT 1",
            (self._app_id, name),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise ValueError(f"Include not found: '{name}'")

        fm = json.loads(row["front_matter"] or "{}")
        return fm.get("_body", "")


async def render_prompt_with_includes(
    template_body: str,
    variables: dict,
    db,
    app_id: str,
) -> str:
    """Render a template that may contain {% include "prompt_name" %} directives.

    Includes are resolved from the prompts table within the same application.
    """
    loader = PromptIncludeLoader(db, app_id)
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
