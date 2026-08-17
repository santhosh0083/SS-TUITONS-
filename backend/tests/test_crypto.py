"""Tests for message encryption at rest."""

import pytest

from app.services import crypto
from app.services.crypto import EncryptionError, decrypt, encrypt

CONV = "11111111-1111-1111-1111-111111111111"
OTHER_CONV = "22222222-2222-2222-2222-222222222222"


@pytest.fixture(autouse=True)
def _configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supply a test key without touching the real environment."""
    from app.core.config import Settings, get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MESSAGE_ENCRYPTION_KEY", "t" * 48)
    monkeypatch.setattr(crypto, "get_settings", lambda: Settings())
    yield
    get_settings.cache_clear()


class TestRoundTrip:
    def test_plaintext_recovered(self) -> None:
        message = "Rahul missed today's class, is everything alright?"
        assert decrypt(encrypt(message, conversation_id=CONV), conversation_id=CONV) == (
            message
        )

    def test_unicode_survives(self) -> None:
        message = "నమస్కారం — తరగతి బాగా జరిగింది 👍"
        assert decrypt(encrypt(message, conversation_id=CONV), conversation_id=CONV) == (
            message
        )

    def test_long_message_survives(self) -> None:
        message = "A" * 20_000
        assert decrypt(encrypt(message, conversation_id=CONV), conversation_id=CONV) == (
            message
        )


class TestCiphertextProperties:
    def test_plaintext_absent_from_ciphertext(self) -> None:
        stored = encrypt("phone number is 9876543210", conversation_id=CONV)
        assert "9876543210" not in stored
        assert "phone" not in stored

    def test_same_message_encrypts_differently(self) -> None:
        """A fresh nonce each time; identical messages must not look identical."""
        a = encrypt("see you at 7", conversation_id=CONV)
        b = encrypt("see you at 7", conversation_id=CONV)
        assert a != b

    def test_version_prefix_present(self) -> None:
        assert encrypt("hello", conversation_id=CONV).startswith("v1:")


class TestTampering:
    def test_message_cannot_be_moved_between_conversations(self) -> None:
        """Conversation id is authenticated, so a row cannot be transplanted
        into a thread it was never part of."""
        stored = encrypt("confidential", conversation_id=CONV)
        with pytest.raises(EncryptionError):
            decrypt(stored, conversation_id=OTHER_CONV)

    def test_modified_ciphertext_rejected(self) -> None:
        stored = encrypt("original message", conversation_id=CONV)
        version, nonce, ct = stored.split(":", 2)
        tampered = f"{version}:{nonce}:{'A' * len(ct)}"
        with pytest.raises(EncryptionError):
            decrypt(tampered, conversation_id=CONV)

    def test_malformed_input_rejected(self) -> None:
        with pytest.raises(EncryptionError):
            decrypt("not-encrypted-at-all", conversation_id=CONV)


class TestRefusals:
    def test_empty_message_refused(self) -> None:
        with pytest.raises(EncryptionError):
            encrypt("", conversation_id=CONV)


class TestMissingKey:
    def test_messaging_refuses_without_a_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a key the system must fail, never fall back to plaintext."""
        from app.core.config import Settings

        monkeypatch.setenv("MESSAGE_ENCRYPTION_KEY", "")
        monkeypatch.setattr(crypto, "get_settings", lambda: Settings())
        assert not crypto.is_configured()
        with pytest.raises(crypto.EncryptionNotConfigured):
            encrypt("hello", conversation_id=CONV)
