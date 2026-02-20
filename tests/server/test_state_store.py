"""Tests for OAuth CSRF state store implementations."""

from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from server.services.state_store import MemoryStateStore


# boto3 is an optional dependency (lambda extra). Create a mock module
# so DynamoDBStateStore can be imported and tested without installing boto3.
_mock_boto3 = MagicMock()


class TestMemoryStateStore:
    @pytest.mark.asyncio
    async def test_put_and_validate(self):
        store = MemoryStateStore()
        await store.put_state("abc123")
        assert await store.validate_state("abc123") is True

    @pytest.mark.asyncio
    async def test_validate_removes_state(self):
        store = MemoryStateStore()
        await store.put_state("abc123")
        assert await store.validate_state("abc123") is True
        # Second validation should fail — state was consumed
        assert await store.validate_state("abc123") is False

    @pytest.mark.asyncio
    async def test_validate_nonexistent_state(self):
        store = MemoryStateStore()
        assert await store.validate_state("nonexistent") is False

    @pytest.mark.asyncio
    async def test_expired_state(self):
        store = MemoryStateStore()
        # Set TTL to 0 seconds (immediately expired)
        await store.put_state("abc123", ttl_seconds=0)
        # Sleep briefly to ensure expiry
        time.sleep(0.01)
        assert await store.validate_state("abc123") is False

    @pytest.mark.asyncio
    async def test_multiple_states(self):
        store = MemoryStateStore()
        await store.put_state("state1")
        await store.put_state("state2")
        assert await store.validate_state("state1") is True
        assert await store.validate_state("state2") is True
        assert await store.validate_state("state1") is False
        assert await store.validate_state("state2") is False


class TestDynamoDBStateStore:
    def _make_store(self, mock_table: MagicMock):
        """Create a DynamoDBStateStore with a pre-mocked DynamoDB table."""
        mock_boto = MagicMock()
        mock_boto.resource.return_value.Table.return_value = mock_table
        with patch.dict(sys.modules, {"boto3": mock_boto}):
            from server.services.state_store import DynamoDBStateStore
            return DynamoDBStateStore("test-table", region="us-east-1")

    @pytest.mark.asyncio
    async def test_put_state_calls_dynamodb(self):
        mock_table = MagicMock()
        store = self._make_store(mock_table)

        await store.put_state("abc123", ttl_seconds=600)

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args[1]["Item"]
        assert item["state"] == "abc123"
        assert "ttl" in item

    @pytest.mark.asyncio
    async def test_validate_state_returns_true_when_exists(self):
        mock_table = MagicMock()
        mock_table.delete_item.return_value = {
            "Attributes": {"state": "abc123", "ttl": 9999999999}
        }
        store = self._make_store(mock_table)

        result = await store.validate_state("abc123")
        assert result is True
        mock_table.delete_item.assert_called_once_with(
            Key={"state": "abc123"}, ReturnValues="ALL_OLD"
        )

    @pytest.mark.asyncio
    async def test_validate_state_returns_false_when_missing(self):
        mock_table = MagicMock()
        mock_table.delete_item.return_value = {}  # No Attributes key
        store = self._make_store(mock_table)

        result = await store.validate_state("nonexistent")
        assert result is False


class TestGetStateStore:
    def test_container_mode_returns_memory_store(self):
        with patch("server.services.state_store.settings") as mock_settings:
            mock_settings.deployment_mode = "container"
            from server.services.state_store import get_state_store
            store = get_state_store()
            assert isinstance(store, MemoryStateStore)

    def test_lambda_mode_returns_dynamodb_store(self):
        mock_boto = MagicMock()
        with patch.dict(sys.modules, {"boto3": mock_boto}):
            with patch("server.services.state_store.settings") as mock_settings:
                mock_settings.deployment_mode = "lambda"
                mock_settings.dynamodb_state_table = "test-table"
                mock_settings.aws_region = "us-east-1"
                from server.services.state_store import get_state_store, DynamoDBStateStore
                store = get_state_store()
                assert isinstance(store, DynamoDBStateStore)
