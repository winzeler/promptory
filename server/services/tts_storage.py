"""TTS audio storage — local filesystem (container) or S3 (Lambda)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from server.config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class TTSStorage(Protocol):
    """Interface for TTS audio file persistence."""

    async def get(self, key: str) -> bytes | None:
        """Retrieve audio bytes by cache key. Returns None on miss."""
        ...

    async def put(self, key: str, data: bytes) -> None:
        """Store audio bytes under cache key."""
        ...

    async def get_url(self, key: str) -> str | None:
        """Return a URL to serve the audio. For local storage, returns the file path.
        For S3, returns a presigned URL. Returns None if not found."""
        ...


class LocalTTSStorage:
    """Container deployment — local filesystem at tts_cache_dir."""

    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.mp3"

    async def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_bytes()

    async def put(self, key: str, data: bytes) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_bytes(data)

    async def get_url(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        return str(path)


class S3TTSStorage:
    """Lambda deployment — S3 bucket with presigned URLs."""

    def __init__(self, bucket_name: str, region: str = "us-west-2") -> None:
        import boto3

        self._bucket = bucket_name
        self._s3 = boto3.client("s3", region_name=region)

    def _key(self, key: str) -> str:
        return f"tts-cache/{key}.mp3"

    async def get(self, key: str) -> bytes | None:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=self._key(key))
            return resp["Body"].read()
        except self._s3.exceptions.NoSuchKey:
            return None
        except Exception:
            logger.debug("S3 get failed for key=%s", key, exc_info=True)
            return None

    async def put(self, key: str, data: bytes) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=self._key(key),
            Body=data,
            ContentType="audio/mpeg",
        )

    async def get_url(self, key: str) -> str | None:
        try:
            # Check existence first
            self._s3.head_object(Bucket=self._bucket, Key=self._key(key))
        except Exception:
            return None
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": self._key(key)},
            ExpiresIn=3600,
        )


def get_tts_storage() -> TTSStorage:
    """Factory: returns the appropriate TTSStorage for the deployment mode."""
    if settings.deployment_mode == "lambda" and settings.s3_tts_bucket:
        return S3TTSStorage(settings.s3_tts_bucket, settings.aws_region)
    return LocalTTSStorage(settings.tts_cache_dir)
