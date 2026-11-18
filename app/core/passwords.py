"""Hash and verify the single administrator password for the private preview."""
from __future__ import annotations

import hashlib
import hmac
import os


def hash_password(password: str) -> str:
    if len(password) < 16:
        raise ValueError("A senha deve ter pelo menos 16 caracteres.")
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        method, n, r, p, salt, expected = encoded.split("$")
        if (method, n, r, p) != ("scrypt", "16384", "8", "1"):
            return False
        salt_bytes, expected_bytes = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 64:
            return False
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt_bytes, n=16384, r=8, p=1)
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError):
        return False
