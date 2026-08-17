"""Tests for password hashing and JWT handling."""

import uuid

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    token_subject,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_then_verify_succeeds(self) -> None:
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h)

    def test_wrong_password_fails(self) -> None:
        h = hash_password("correct horse battery staple")
        assert not verify_password("wrong password", h)

    def test_hash_is_not_plaintext(self) -> None:
        h = hash_password("hunter2")
        assert "hunter2" not in h
        assert h.startswith("$argon2id$")

    def test_same_password_hashes_differently(self) -> None:
        """Salting means two hashes of one password must not match."""
        assert hash_password("same") != hash_password("same")

    def test_malformed_hash_returns_false_not_exception(self) -> None:
        assert not verify_password("anything", "not-a-real-hash")

    def test_empty_password_still_verifies_correctly(self) -> None:
        h = hash_password("")
        assert verify_password("", h)
        assert not verify_password("x", h)


class TestAccessTokens:
    def test_round_trip_preserves_subject(self) -> None:
        uid = uuid.uuid4()
        payload = decode_token(create_access_token(uid), "access")
        assert token_subject(payload) == uid

    def test_roles_are_embedded(self) -> None:
        payload = decode_token(
            create_access_token(uuid.uuid4(), roles=["TUTOR"]), "access"
        )
        assert payload["roles"] == ["TUTOR"]

    def test_each_token_has_unique_jti(self) -> None:
        uid = uuid.uuid4()
        a = decode_token(create_access_token(uid), "access")["jti"]
        b = decode_token(create_access_token(uid), "access")["jti"]
        assert a != b


class TestTokenTypeConfusion:
    """A refresh token must never be usable as an access token."""

    def test_refresh_token_rejected_as_access(self) -> None:
        token = create_refresh_token(uuid.uuid4())
        with pytest.raises(TokenError, match="Expected a access token"):
            decode_token(token, "access")

    def test_access_token_rejected_as_refresh(self) -> None:
        token = create_access_token(uuid.uuid4())
        with pytest.raises(TokenError, match="Expected a refresh token"):
            decode_token(token, "refresh")


class TestTokenTampering:
    def test_garbage_token_rejected(self) -> None:
        with pytest.raises(TokenError):
            decode_token("not.a.token", "access")

    def test_modified_payload_rejected(self) -> None:
        token = create_access_token(uuid.uuid4())
        head, payload, sig = token.split(".")
        tampered = f"{head}.{payload[:-4]}AAAA.{sig}"
        with pytest.raises(TokenError):
            decode_token(tampered, "access")

    def test_signature_stripped_rejected(self) -> None:
        head, payload, _ = create_access_token(uuid.uuid4()).split(".")
        with pytest.raises(TokenError):
            decode_token(f"{head}.{payload}.", "access")


class TestRefreshTokenStorage:
    def test_hash_is_deterministic(self) -> None:
        token = create_refresh_token(uuid.uuid4())
        assert hash_refresh_token(token) == hash_refresh_token(token)

    def test_hash_does_not_contain_token(self) -> None:
        token = create_refresh_token(uuid.uuid4())
        assert token not in hash_refresh_token(token)

    def test_distinct_tokens_hash_differently(self) -> None:
        a = hash_refresh_token(create_refresh_token(uuid.uuid4()))
        b = hash_refresh_token(create_refresh_token(uuid.uuid4()))
        assert a != b
