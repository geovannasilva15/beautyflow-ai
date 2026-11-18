"""Password hashing for BeautyFlow accounts."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from threading import BoundedSemaphore

_workers = BoundedSemaphore(2)


def _derive(password: str, salt: bytes) -> bytes:
    with _workers:
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=32768, r=8, p=3,
            maxmem=64 * 1024 * 1024, dklen=32,
        )


def hash_password(password: str) -> str:
    if not 16 <= len(password) <= 128:
        raise ValueError("A senha deve ter entre 16 e 128 caracteres.")
    salt = secrets.token_bytes(16)
    return f"scrypt$32768$8$3${salt.hex()}${_derive(password, salt).hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        method, n, r, p, salt, expected = encoded.split("$")
        if (method, n, r, p) != ("scrypt", "32768", "8", "3"):
            return False
        salt_bytes, expected_bytes = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 32:
            return False
        return hmac.compare_digest(_derive(password, salt_bytes), expected_bytes)
    except (ValueError, TypeError):
        return False
