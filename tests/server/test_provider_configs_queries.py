"""Tests for provider_configs CRUD queries."""

from __future__ import annotations

import pytest

from server.db.queries import provider_configs as pc_queries

from tests.conftest import APP_ID


class TestProviderConfigsCRUD:
    @pytest.mark.asyncio
    async def test_upsert_and_get(self, db):
        config_id = await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            config_json={"organization": "org-123"},
            secrets={"api_key": "sk-test"},
        )
        assert config_id is not None

        config = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        assert config is not None
        assert config["provider"] == "openai"
        assert config["scope"] == "app"
        assert config["config_json"]["organization"] == "org-123"
        assert config["secrets"]["api_key"] == "sk-test"

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db):
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-old"},
        )
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-new"},
        )
        config = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        assert config["secrets"]["api_key"] == "sk-new"

    @pytest.mark.asyncio
    async def test_upsert_preserves_secrets_when_not_provided(self, db):
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-keep"},
        )
        # Update config without secrets
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            config_json={"organization": "org-456"},
        )
        config = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        assert config["secrets"]["api_key"] == "sk-keep"
        assert config["config_json"]["organization"] == "org-456"

    @pytest.mark.asyncio
    async def test_list_provider_configs(self, db):
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai", secrets={"api_key": "sk-1"},
        )
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "anthropic", secrets={"api_key": "sk-2"},
        )
        configs = await pc_queries.list_provider_configs(db, "app", APP_ID)
        assert len(configs) == 2
        providers = {c["provider"] for c in configs}
        assert providers == {"openai", "anthropic"}

    @pytest.mark.asyncio
    async def test_delete(self, db):
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai", secrets={"api_key": "sk-del"},
        )
        deleted = await pc_queries.delete_provider_config(db, "app", APP_ID, "openai")
        assert deleted is True
        config = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        assert config is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db):
        deleted = await pc_queries.delete_provider_config(db, "app", APP_ID, "nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_environment_scoped_configs(self, db):
        """Same provider can have different configs per environment."""
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-all"},
        )
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            environment="production",
            secrets={"api_key": "sk-prod"},
        )
        all_env = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        prod_env = await pc_queries.get_provider_config(db, "app", APP_ID, "openai", "production")
        assert all_env["secrets"]["api_key"] == "sk-all"
        assert prod_env["secrets"]["api_key"] == "sk-prod"

    @pytest.mark.asyncio
    async def test_mask_secrets(self, db):
        await pc_queries.upsert_provider_config(
            db, "app", APP_ID, "openai",
            secrets={"api_key": "sk-1234567890abcdef"},
        )
        config = await pc_queries.get_provider_config(db, "app", APP_ID, "openai")
        masked = pc_queries.mask_secrets(config)
        assert masked["secrets"]["api_key"] == "sk-1...cdef"
        assert masked["secrets"]["has_api_key"] is True
        # Internal keys should be stripped
        assert "_secrets_encrypted_raw" not in masked
