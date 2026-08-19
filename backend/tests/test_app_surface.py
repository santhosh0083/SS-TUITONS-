"""Tests for what the deployed app exposes to the public internet.

Both properties here were found missing on the live service, not in review:
/docs answered 200 in production, and FORCE_HTTPS was required at boot while
being read by nothing. Neither shows up in normal use — the app works fine
either way — so they need a test to stay fixed.
"""

import importlib

import pytest
from fastapi.testclient import TestClient


def _app_with(monkeypatch: pytest.MonkeyPatch, **env: str):
    """Build the app fresh under the given environment.

    Settings are cached with lru_cache and main.py reads them at import time,
    so both have to be reloaded for an environment change to take effect.
    """
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import app.core.config as config

    config.get_settings.cache_clear()

    import app.main as main

    importlib.reload(main)
    return main.app


PRODUCTION = {
    "APP_ENV": "production",
    "JWT_SECRET": "x" * 64,
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "none",
    "FORCE_HTTPS": "true",
    "FRONTEND_BASE_URL": "https://ss-tuitons.vercel.app",
    "BACKEND_BASE_URL": "https://ss-tuitons-1.onrender.com",
}


class TestInteractiveDocs:
    """The docs enumerate every route and schema, including the admin surface."""

    @pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
    def test_not_served_in_production(
        self, monkeypatch: pytest.MonkeyPatch, path: str
    ) -> None:
        app = _app_with(monkeypatch, **PRODUCTION)
        with TestClient(app) as client:
            assert client.get(path).status_code == 404

    @pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
    def test_served_in_development(
        self, monkeypatch: pytest.MonkeyPatch, path: str
    ) -> None:
        # Turning them off everywhere would make local work harder for no gain.
        app = _app_with(monkeypatch, APP_ENV="development")
        with TestClient(app) as client:
            assert client.get(path).status_code == 200


class TestSecurityHeaders:
    def test_hsts_present_when_force_https(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = _app_with(monkeypatch, **PRODUCTION)
        with TestClient(app) as client:
            header = client.get("/api/v1/health").headers.get(
                "strict-transport-security"
            )
        assert header is not None, "FORCE_HTTPS=true must actually do something"
        assert "max-age=" in header

    def test_no_hsts_without_force_https(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Sending HSTS from a local http:// server would pin the browser to
        # https for localhost and break development for every other project.
        app = _app_with(monkeypatch, APP_ENV="development", FORCE_HTTPS="false")
        with TestClient(app) as client:
            headers = client.get("/api/v1/health").headers
        assert "strict-transport-security" not in headers

    def test_content_type_options_always_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = _app_with(monkeypatch, APP_ENV="development")
        with TestClient(app) as client:
            headers = client.get("/api/v1/health").headers
        assert headers.get("x-content-type-options") == "nosniff"
