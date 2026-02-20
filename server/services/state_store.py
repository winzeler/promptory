"""OAuth CSRF state store — in-memory (container) or DynamoDB (Lambda)."""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable

from server.config import settings


@runtime_checkable
class StateStore(Protocol):
    """Interface for OAuth CSRF state persistence."""

    async def put_state(self, state: str, ttl_seconds: int = 600) -> None: ...

    async def validate_state(self, state: str) -> bool: ...


class MemoryStateStore:
    """Container deployment — in-memory dict (single-process safe)."""

    def __init__(self) -> None:
        self._states: dict[str, float] = {}

    async def put_state(self, state: str, ttl_seconds: int = 600) -> None:
        self._states[state] = time.time() + ttl_seconds

    async def validate_state(self, state: str) -> bool:
        expires_at = self._states.pop(state, None)
        if expires_at is None:
            return False
        return time.time() < expires_at


class DynamoDBStateStore:
    """Lambda deployment — DynamoDB with TTL auto-expiry."""

    def __init__(self, table_name: str, region: str = "us-west-2") -> None:
        import boto3

        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    async def put_state(self, state: str, ttl_seconds: int = 600) -> None:
        self._table.put_item(
            Item={"state": state, "ttl": int(time.time()) + ttl_seconds}
        )

    async def validate_state(self, state: str) -> bool:
        resp = self._table.delete_item(
            Key={"state": state}, ReturnValues="ALL_OLD"
        )
        return "Attributes" in resp


def get_state_store() -> StateStore:
    """Factory: returns the appropriate StateStore for the deployment mode."""
    if settings.deployment_mode == "lambda":
        return DynamoDBStateStore(
            settings.dynamodb_state_table, settings.aws_region
        )
    return MemoryStateStore()
