"""Password hashing for control-plane admin users."""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash a password using a random salt and scrypt key derivation.

    Returns an encoded ``scrypt$salt$hex-digest`` verifier. The input is
    UTF-8 encoded; plaintext is not included in the returned value. This helper
    does not impose password policy or provide login rate limiting.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a plaintext candidate against an encoded scrypt verifier.

    Returns ``False`` for malformed values or unsupported algorithms and uses
    constant-time digest comparison for valid scrypt records. Invalid scrypt
    parameters/digests may raise from the underlying hashing implementation.
    """
    try:
        algo, salt, hex_hash = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return secrets.compare_digest(digest.hex(), hex_hash)
