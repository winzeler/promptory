"""Encryption utilities for storing sensitive data (GitHub tokens)."""

from __future__ import annotations

from cryptography.fernet import Fernet

from server.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        # Derive a Fernet key from the app secret (must be 32 url-safe base64 bytes)
        import base64
        import hashlib

        key_bytes = hashlib.sha256(settings.app_secret_key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        _fernet = Fernet(fernet_key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext and return plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
