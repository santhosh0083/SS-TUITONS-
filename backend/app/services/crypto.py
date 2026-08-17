"""Message encryption at rest.

WHAT THIS IS
------------
AES-256-GCM encryption of message bodies using a key held by the server. The
database stores only ciphertext, so a leaked database dump — the most likely
breach for a small platform — does not expose what parents and tutors wrote.

WHAT THIS IS NOT
----------------
This is NOT end-to-end encryption. The server holds the key and can decrypt any
message. That is a deliberate product decision: SS Tuitions must be able to
review conversations for child-safety reasons, and true E2EE would make that
impossible.

Nothing in this codebase or its UI may describe messaging as "end-to-end
encrypted". Saying so would be false, and for a platform serving minors a false
privacy claim is worse than an honest weaker one.

THREAT MODEL — what this protects against, and what it does not
---------------------------------------------------------------
Protects against:
  * A stolen or leaked database backup
  * A read-only SQL breach, or a curious person with database console access
  * A support engineer browsing rows in the Supabase dashboard

Does NOT protect against:
  * An attacker who obtains MESSAGE_ENCRYPTION_KEY (kept out of the database,
    in environment config only)
  * A compromised application server, which by definition holds the key
  * A legitimate admin — decryption by admins is a feature, and every instance
    is written to the audit log

KEY ROTATION
------------
Ciphertext is prefixed with a key version, so a future key can be introduced
without rewriting existing rows. Old messages stay readable with the old key.
"""

import base64
import hashlib
import logging

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Bumped when the key changes. Stored with each ciphertext.
CURRENT_KEY_VERSION = 1
_NONCE_BYTES = 12  # 96 bits, the size AES-GCM is specified for


class EncryptionError(Exception):
    """Encryption or decryption failed. Never shown to an end user."""


class EncryptionNotConfigured(EncryptionError):
    """No key set. Messaging must refuse to operate rather than store plaintext."""


def _key_material() -> bytes:
    """Derive a 32-byte AES key from the configured secret.

    SHA-256 of the configured value, so any sufficiently long secret works
    without requiring the operator to produce exactly 32 raw bytes.
    """
    secret = get_settings().message_encryption_key
    if not secret or len(secret) < 32:
        raise EncryptionNotConfigured(
            "MESSAGE_ENCRYPTION_KEY must be set to at least 32 characters. "
            "Generate one with: python -c \"import secrets; "
            'print(secrets.token_urlsafe(48))"'
        )
    return hashlib.sha256(secret.encode("utf-8")).digest()


def is_configured() -> bool:
    try:
        _key_material()
    except EncryptionNotConfigured:
        return False
    return True


def encrypt(plaintext: str, *, conversation_id: str) -> str:
    """Encrypt a message body.

    Returns "v1:<base64 nonce>:<base64 ciphertext>".

    `conversation_id` is bound in as additional authenticated data, so a
    ciphertext row cannot be moved from one conversation to another — an
    attacker with write access cannot transplant a message into a thread it was
    never part of.
    """
    if not plaintext:
        raise EncryptionError("Refusing to encrypt an empty message")

    aes = AESGCM(_key_material())
    nonce = _random_nonce()
    ciphertext = aes.encrypt(
        nonce, plaintext.encode("utf-8"), conversation_id.encode("utf-8")
    )
    return (
        f"v{CURRENT_KEY_VERSION}:"
        f"{base64.b64encode(nonce).decode()}:"
        f"{base64.b64encode(ciphertext).decode()}"
    )


def decrypt(stored: str, *, conversation_id: str) -> str:
    """Decrypt a stored message body."""
    try:
        version, nonce_b64, ct_b64 = stored.split(":", 2)
    except ValueError as exc:
        raise EncryptionError("Stored message is not in the expected format") from exc

    if version != f"v{CURRENT_KEY_VERSION}":
        raise EncryptionError(f"Message uses unsupported key version {version!r}")

    try:
        aes = AESGCM(_key_material())
        plaintext = aes.decrypt(
            base64.b64decode(nonce_b64),
            base64.b64decode(ct_b64),
            conversation_id.encode("utf-8"),
        )
    except InvalidTag as exc:
        # Wrong key, tampered ciphertext, or wrong conversation.
        raise EncryptionError("Message could not be decrypted") from exc
    except Exception as exc:
        raise EncryptionError("Message could not be decrypted") from exc

    return plaintext.decode("utf-8")


def _random_nonce() -> bytes:
    import os

    return os.urandom(_NONCE_BYTES)
