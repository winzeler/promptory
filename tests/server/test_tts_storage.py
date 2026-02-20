"""Tests for TTS audio storage implementations."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from server.services.tts_storage import LocalTTSStorage


class TestLocalTTSStorage:
    @pytest.mark.asyncio
    async def test_put_and_get(self, tmp_path):
        storage = LocalTTSStorage(str(tmp_path / "tts_cache"))
        audio_data = b"\xff\xfb\x90\x00" * 100

        await storage.put("test-key", audio_data)
        result = await storage.get("test-key")

        assert result == audio_data

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, tmp_path):
        storage = LocalTTSStorage(str(tmp_path / "tts_cache"))
        result = await storage.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_url_returns_path(self, tmp_path):
        storage = LocalTTSStorage(str(tmp_path / "tts_cache"))
        audio_data = b"\xff\xfb\x90\x00" * 100

        await storage.put("test-key", audio_data)
        url = await storage.get_url("test-key")

        assert url is not None
        assert url.endswith("test-key.mp3")

    @pytest.mark.asyncio
    async def test_get_url_missing_returns_none(self, tmp_path):
        storage = LocalTTSStorage(str(tmp_path / "tts_cache"))
        url = await storage.get_url("nonexistent")
        assert url is None

    @pytest.mark.asyncio
    async def test_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "nested" / "tts_cache"
        storage = LocalTTSStorage(str(cache_dir))
        await storage.put("test-key", b"data")
        assert cache_dir.exists()


class TestS3TTSStorage:
    def _make_storage(self, mock_s3: MagicMock):
        """Create an S3TTSStorage with a pre-mocked S3 client."""
        mock_boto = MagicMock()
        mock_boto.client.return_value = mock_s3
        with patch.dict(sys.modules, {"boto3": mock_boto}):
            from server.services.tts_storage import S3TTSStorage
            return S3TTSStorage("test-bucket", region="us-east-1")

    @pytest.mark.asyncio
    async def test_put_calls_s3(self):
        mock_s3 = MagicMock()
        storage = self._make_storage(mock_s3)

        await storage.put("test-key", b"\xff\xfb\x90\x00")

        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="tts-cache/test-key.mp3",
            Body=b"\xff\xfb\x90\x00",
            ContentType="audio/mpeg",
        )

    @pytest.mark.asyncio
    async def test_get_returns_bytes(self):
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"\xff\xfb\x90\x00"
        mock_s3.get_object.return_value = {"Body": mock_body}
        storage = self._make_storage(mock_s3)

        result = await storage.get("test-key")
        assert result == b"\xff\xfb\x90\x00"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        mock_s3 = MagicMock()
        mock_s3.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})
        mock_s3.get_object.side_effect = mock_s3.exceptions.NoSuchKey("not found")
        storage = self._make_storage(mock_s3)

        result = await storage.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_url_returns_presigned_url(self):
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/tts-cache/test-key.mp3?sig=abc"
        )
        storage = self._make_storage(mock_s3)

        url = await storage.get_url("test-key")
        assert url is not None
        assert url.startswith("https://")
        mock_s3.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_url_missing_returns_none(self):
        mock_s3 = MagicMock()
        mock_s3.head_object.side_effect = Exception("not found")
        storage = self._make_storage(mock_s3)

        url = await storage.get_url("nonexistent")
        assert url is None


class TestGetTTSStorage:
    def test_container_mode_returns_local_storage(self):
        with patch("server.services.tts_storage.settings") as mock_settings:
            mock_settings.deployment_mode = "container"
            mock_settings.tts_cache_dir = "/tmp/tts_test"
            from server.services.tts_storage import get_tts_storage
            storage = get_tts_storage()
            assert isinstance(storage, LocalTTSStorage)

    def test_lambda_mode_returns_s3_storage(self):
        mock_boto = MagicMock()
        with patch.dict(sys.modules, {"boto3": mock_boto}):
            with patch("server.services.tts_storage.settings") as mock_settings:
                mock_settings.deployment_mode = "lambda"
                mock_settings.s3_tts_bucket = "test-bucket"
                mock_settings.aws_region = "us-east-1"
                from server.services.tts_storage import get_tts_storage, S3TTSStorage
                storage = get_tts_storage()
                assert isinstance(storage, S3TTSStorage)

    def test_lambda_mode_no_bucket_falls_back_to_local(self):
        with patch("server.services.tts_storage.settings") as mock_settings:
            mock_settings.deployment_mode = "lambda"
            mock_settings.s3_tts_bucket = ""
            mock_settings.tts_cache_dir = "/tmp/tts_test"
            from server.services.tts_storage import get_tts_storage
            storage = get_tts_storage()
            assert isinstance(storage, LocalTTSStorage)
