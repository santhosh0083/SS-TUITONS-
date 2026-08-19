"""Tests for how email leaves the building.

Written after every password reset, fee reminder and payment receipt failed
silently in production for days. Render's free plan blocks outbound SMTP, so
smtplib raised OSError, send() swallowed it by design, and the endpoint still
answered 200. Nothing was broken enough to notice.

These lock in the two things that would have surfaced it: the provider is
selectable, and is_configured() answers for the transport actually in use.
"""

import smtplib

import httpx
import pytest

from app.core.config import Settings
from app.services import email


def _settings(**overrides) -> Settings:
    base = {
        "email_enabled": True,
        "email_from_address": "sstuitions42@gmail.com",
        "email_from_name": "SS Tuitions",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def as_settings(monkeypatch: pytest.MonkeyPatch):
    def apply(**overrides):
        s = _settings(**overrides)
        monkeypatch.setattr(email, "get_settings", lambda: s)
        return s

    return apply


class TestConfiguration:
    def test_brevo_needs_only_an_api_key(self, as_settings) -> None:
        as_settings(email_provider="brevo", brevo_api_key="xkeysib-test")
        assert email.is_configured()

    def test_brevo_without_key_is_not_configured(self, as_settings) -> None:
        as_settings(email_provider="brevo", brevo_api_key="")
        assert not email.is_configured()
        assert "BREVO_API_KEY" in email.configuration_hint()

    def test_smtp_credentials_do_not_configure_brevo(self, as_settings) -> None:
        # The trap: SMTP settings present, provider switched to brevo, and the
        # app reporting healthy while nothing can send.
        as_settings(
            email_provider="brevo",
            brevo_api_key="",
            email_smtp_user="someone@gmail.com",
            email_smtp_password="app-password",
        )
        assert not email.is_configured()

    def test_smtp_is_configured_with_credentials(self, as_settings) -> None:
        as_settings(
            email_provider="smtp",
            email_smtp_user="someone@gmail.com",
            email_smtp_password="app-password",
        )
        assert email.is_configured()

    def test_disabled_is_never_configured(self, as_settings) -> None:
        as_settings(
            email_enabled=False, email_provider="brevo", brevo_api_key="xkeysib-test"
        )
        assert not email.is_configured()


class TestBrevoTransport:
    def test_posts_to_brevo_and_reports_success(
        self, as_settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        as_settings(email_provider="brevo", brevo_api_key="xkeysib-test")
        seen: dict = {}

        def fake_post(url, json, headers, timeout):
            seen["url"] = url
            seen["json"] = json
            seen["headers"] = headers
            return httpx.Response(201, json={"messageId": "abc"})

        monkeypatch.setattr(email.httpx, "post", fake_post)

        assert email.send(to="parent@example.com", subject="Fee received", body_text="hi")
        assert seen["url"] == email.BREVO_ENDPOINT
        assert seen["headers"]["api-key"] == "xkeysib-test"
        assert seen["json"]["to"] == [{"email": "parent@example.com"}]
        assert seen["json"]["sender"]["email"] == "sstuitions42@gmail.com"

    def test_refusal_is_reported_not_raised(
        self, as_settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An unverified sender returns 400. Recording a payment must still
        # succeed even though its receipt cannot be delivered.
        as_settings(email_provider="brevo", brevo_api_key="xkeysib-test")
        monkeypatch.setattr(
            email.httpx,
            "post",
            lambda *a, **k: httpx.Response(400, json={"message": "sender not valid"}),
        )
        assert email.send(to="p@example.com", subject="x", body_text="y") is False

    def test_network_failure_is_reported_not_raised(
        self, as_settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        as_settings(email_provider="brevo", brevo_api_key="xkeysib-test")

        def boom(*a, **k):
            raise httpx.ConnectError("no route")

        monkeypatch.setattr(email.httpx, "post", boom)
        assert email.send(to="p@example.com", subject="x", body_text="y") is False


class TestSmtpTransport:
    def test_blocked_port_is_reported_not_raised(
        self, as_settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact production failure: OSError 101 from a blocked SMTP port."""
        as_settings(
            email_provider="smtp",
            email_smtp_user="someone@gmail.com",
            email_smtp_password="app-password",
        )

        def blocked(*a, **k):
            raise OSError(101, "Network is unreachable")

        monkeypatch.setattr(smtplib, "SMTP", blocked)
        assert email.send(to="p@example.com", subject="x", body_text="y") is False

    def test_unconfigured_send_returns_false(self, as_settings) -> None:
        as_settings(email_provider="smtp", email_smtp_password="")
        assert email.send(to="p@example.com", subject="x", body_text="y") is False
