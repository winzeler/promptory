"""Tests for the credential resolution service."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from server.db.queries import provider_configs as pc_queries
from server.services.credential_service import (
    resolve_credential,
    resolve_eval_env_vars,
)

from tests.conftest import APP_ID, USER_ID


class TestResolveCredential:
    @pytest.mark.asyncio
    async def test_resolve_app_level_credential(self, db):
        """App-level secret returned when set."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-app-key"},
        )
        cred = await resolve_credential(db, "openai", app_id=APP_ID)
        assert cred is not None
        assert cred["api_key"] == "sk-app-key"
        assert cred["_source"] == "app"

    @pytest.mark.asyncio
    async def test_resolve_user_level_fallback(self, db):
        """User-level returned when no app-level exists."""
        await pc_queries.upsert_provider_config(
            db, "user", USER_ID, "openai",
            secrets={"api_key": "sk-user-key"},
        )
        cred = await resolve_credential(db, "openai", app_id=APP_ID, user_id=USER_ID)
        assert cred is not None
        assert cred["api_key"] == "sk-user-key"
        assert cred["_source"] == "user"

    @pytest.mark.asyncio
    async def test_resolve_env_var_fallback(self, db):
        """Env var returned when no DB configs exist."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"}):
            cred = await resolve_credential(db, "openai", app_id=APP_ID)
        assert cred is not None
        assert cred["api_key"] == "sk-env-key"
        assert cred["_source"] == "global"

    @pytest.mark.asyncio
    async def test_resolve_cascade_priority(self, db):
        """App-level beats user-level beats env var."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-app-key"},
        )
        await pc_queries.upsert_provider_config(
            db, "user", USER_ID, "openai",
            secrets={"api_key": "sk-user-key"},
        )
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"}):
            cred = await resolve_credential(db, "openai", app_id=APP_ID, user_id=USER_ID)
        assert cred["api_key"] == "sk-app-key"

    @pytest.mark.asyncio
    async def test_resolve_no_credential(self, db):
        """Returns None when nothing is configured."""
        with patch.dict("os.environ", {}, clear=True):
            cred = await resolve_credential(db, "openai", app_id=APP_ID)
        assert cred is None

    @pytest.mark.asyncio
    async def test_resolve_env_specific_credential(self, db):
        """Environment-specific key beats all-env key."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-all-env"},
        )
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            environment="production",
            secrets={"api_key": "sk-prod-key"},
        )
        cred = await resolve_credential(
            db, "openai", app_id=APP_ID, environment="production"
        )
        assert cred["api_key"] == "sk-prod-key"

    @pytest.mark.asyncio
    async def test_resolve_env_fallback_to_null(self, db):
        """NULL env config used when no env-specific match."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-all-env"},
        )
        cred = await resolve_credential(
            db, "openai", app_id=APP_ID, environment="staging"
        )
        assert cred["api_key"] == "sk-all-env"

    @pytest.mark.asyncio
    async def test_resolve_elevenlabs_settings_fallback(self, db):
        """ElevenLabs falls back to settings.elevenlabs_api_key."""
        with patch("server.config.settings") as mock_settings:
            mock_settings.elevenlabs_api_key = "el-global-key"
            cred = await resolve_credential(db, "elevenlabs", app_id=APP_ID)
        assert cred is not None
        assert cred["api_key"] == "el-global-key"


class TestResolveEvalEnvVars:
    @pytest.mark.asyncio
    async def test_multi_model_resolution(self, db):
        """Builds correct env dict for multiple providers."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-openai"},
        )
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "anthropic",
            secrets={"api_key": "sk-anthropic"},
        )

        env_vars = await resolve_eval_env_vars(
            db, ["gpt-4o", "claude-sonnet-4-5-20250929"], app_id=APP_ID,
        )
        assert env_vars["OPENAI_API_KEY"] == "sk-openai"
        assert env_vars["ANTHROPIC_API_KEY"] == "sk-anthropic"

    @pytest.mark.asyncio
    async def test_unknown_model_skipped(self, db):
        """Unknown models don't break resolution."""
        env_vars = await resolve_eval_env_vars(
            db, ["custom-model-v1"], app_id=APP_ID,
        )
        assert env_vars == {}

    @pytest.mark.asyncio
    async def test_deduplicates_providers(self, db):
        """Multiple models from same provider only resolve once."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-openai"},
        )
        env_vars = await resolve_eval_env_vars(
            db, ["gpt-4o", "gpt-4o-mini"], app_id=APP_ID,
        )
        assert len(env_vars) == 1
        assert env_vars["OPENAI_API_KEY"] == "sk-openai"


class TestSecretsEncryption:
    @pytest.mark.asyncio
    async def test_secrets_encrypted_at_rest(self, db):
        """Verify secrets are Fernet-encrypted in the database."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-test-secret"},
        )
        # Read raw from DB
        async with db.execute(
            "SELECT secrets_encrypted FROM provider_configs WHERE scope = 'app' AND scope_id = ? AND provider = 'openai'",
            (APP_ID,),
        ) as cursor:
            row = await cursor.fetchone()

        raw = row[0]
        assert raw is not None
        # Raw value should NOT contain the plaintext
        assert "sk-test-secret" not in raw
        # But decrypting should recover it
        from server.utils.crypto import decrypt
        decrypted = json.loads(decrypt(raw))
        assert decrypted["api_key"] == "sk-test-secret"
