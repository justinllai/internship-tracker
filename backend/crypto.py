# ============================================================
# crypto.py — Encrypt Gmail refresh tokens before storing them
# ------------------------------------------------------------
# A Google refresh token is a long-lived key to someone's
# inbox. If our database ever leaked, plaintext tokens would be
# a disaster. So we encrypt them "at rest" with Fernet
# (AES + HMAC from the `cryptography` library). The key lives
# only in an environment variable, never in the database.
#
# Why not hash them like passwords? Hashing is one-way: we can
# CHECK a password against a hash, but we need the actual
# token back to call Google. That requires reversible
# encryption.
#
# MultiFernet = key rotation. TOKEN_ENCRYPTION_KEYS is a list,
# newest first. Encryption always uses the newest key;
# decryption tries each key in order. So you can roll out a
# new key without breaking existing users.
#
# Generate a key:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ============================================================

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

import config


class TokenDecryptError(Exception):
    """The stored token can't be decrypted (key lost/rotated away)."""


def _fernet() -> MultiFernet:
    if not config.TOKEN_ENCRYPTION_KEYS:
        raise RuntimeError("TOKEN_ENCRYPTION_KEYS is not set")
    return MultiFernet([Fernet(k.encode()) for k in config.TOKEN_ENCRYPTION_KEYS])


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise TokenDecryptError("stored token could not be decrypted") from e


def rotate(ciphertext: str) -> str:
    """Re-encrypt with the newest key (no-op if already newest)."""
    return _fernet().rotate(ciphertext.encode()).decode()
