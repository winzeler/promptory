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
