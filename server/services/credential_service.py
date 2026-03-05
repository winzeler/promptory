"""Credential resolution service — cascading lookup for provider API keys."""

from __future__ import annotations

import os
import logging

import aiosqlite

from server.db.queries import provider_configs as pc_queries
from server.services.provider_registry import (
    get_provider_for_model,
    ENV_VAR_NAMES,
)

logger = logging.getLogger(__name__)


async def resolve_credential(
    db: aiosqlite.Connection,
    provider: str,
    app_id: str | None = None,
    user_id: str | None = None,
    environment: str | None = None,
) -> dict | None:
    """Resolve a provider credential using the cascade:

    1. App-level + matching environment
    2. App-level + environment=NULL (all-env fallback)
    3. User-level + matching environment
    4. User-level + environment=NULL
    5. Global env var (backward compat)

    Returns the secrets dict (e.g. {"api_key": "sk-..."}) or None.
    """
    # 1 & 2: App-level
    if app_id:
        cred = await _lookup(db, "app", app_id, provider, environment)
        if cred:
            return cred

    # 3 & 4: User-level
    if user_id:
        cred = await _lookup(db, "user", user_id, provider, environment)
        if cred:
            return cred

    # 5: Global env var fallback
    env_var = ENV_VAR_NAMES.get(provider)
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return {"api_key": value, "_source": "global"}

    # Special case: elevenlabs via settings (backward compat)
    if provider == "elevenlabs":
        from server.config import settings
        if settings.elevenlabs_api_key:
            return {"api_key": settings.elevenlabs_api_key, "_source": "global"}

    return None


async def _lookup(
    db: aiosqlite.Connection,
    scope: str,
    scope_id: str,
    provider: str,
    environment: str | None,
) -> dict | None:
    """Try env-specific then all-env config for a given scope."""
    # Try environment-specific first
    if environment:
        config = await pc_queries.get_provider_config(
            db, scope, scope_id, provider, environment
        )
        if config and config.get("secrets"):
            config["secrets"]["_source"] = scope
            return config["secrets"]

    # Fall back to environment=NULL (all-env)
    config = await pc_queries.get_provider_config(
        db, scope, scope_id, provider, environment=None
    )
    if config and config.get("secrets"):
        config["secrets"]["_source"] = scope
        return config["secrets"]

    return None


async def resolve_eval_env_vars(
    db: aiosqlite.Connection,
    models: list[str],
    app_id: str | None = None,
    user_id: str | None = None,
    environment: str | None = None,
) -> dict[str, str]:
    """Build env var dict for promptfoo subprocess from resolved credentials.

    Maps each model to its provider, resolves the credential, and returns
    a dict like {"OPENAI_API_KEY": "sk-...", "ANTHROPIC_API_KEY": "sk-..."}.
    """
    env_vars: dict[str, str] = {}
    seen_providers: set[str] = set()

    for model in models:
        provider = get_provider_for_model(model)
        if not provider or provider in seen_providers:
            continue
        seen_providers.add(provider)

        cred = await resolve_credential(db, provider, app_id, user_id, environment)
        if cred:
            env_var = ENV_VAR_NAMES.get(provider)
            api_key = cred.get("api_key")
            if env_var and api_key:
                env_vars[env_var] = api_key

    return env_vars


async def resolve_provider_status(
    db: aiosqlite.Connection,
    app_id: str,
    user_id: str | None = None,
) -> dict[str, dict]:
    """Show resolution source per provider for status display.

    Returns e.g. {"openai": {"source": "app", "configured": true}, ...}
    """
    from server.services.provider_registry import PROVIDERS

    status: dict[str, dict] = {}
    for provider_name in PROVIDERS:
        cred = await resolve_credential(db, provider_name, app_id, user_id)
        if cred:
            status[provider_name] = {
                "configured": True,
                "source": cred.get("_source", "unknown"),
            }
        else:
            status[provider_name] = {"configured": False, "source": None}

    return status
