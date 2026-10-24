"""Password hashing helpers for the legacy SQLite admin table."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Tuple

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{_ALGORITHM}${_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, stored_value: str) -> Tuple[bool, bool]:
    """Return (valid, needs_rehash); recognize old plaintext rows only for migration."""
    if not password or not stored_value:
        return False, False
    parts = stored_value.split("$")
    if len(parts) == 4 and parts[0] == _ALGORITHM:
        try:
            iterations = int(parts[1])
            if not 10_000 <= iterations <= 1_000_000:
                return False, False
            salt = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
            expected = base64.urlsafe_b64decode(parts[3] + "=" * (-len(parts[3]) % 4))
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        except (ValueError, TypeError):
            return False, False
        valid = hmac.compare_digest(actual, expected)
        return valid, valid and iterations < _ITERATIONS

    # Upgrade existing installations after a successful login without invalidating accounts.
    return hmac.compare_digest(password.encode("utf-8"), stored_value.encode("utf-8")), True
