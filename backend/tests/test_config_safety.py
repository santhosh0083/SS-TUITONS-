"""Tests for the production configuration guard.

These exist because the failures they catch are silent. A cross-site cookie
misconfiguration produces a login that returns 200 and then does not persist —
it looks like it works until a real parent tries to use it.
"""

import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "app_env": "production",
        "jwt_secret": "x" * 64,
        "cookie_secure": True,
        "force_https": True,
        "cookie_samesite": "none",
        "frontend_base_url": "https://sstuitions.vercel.app",
        "backend_base_url": "https://ss-api.onrender.com",
    }
    base.update(overrides)
    return Settings(**base)


class TestCrossSiteDetection:
    def test_different_domains_are_cross_site(self) -> None:
        s = _settings()
        assert s.is_cross_site

    def test_subdomains_of_one_domain_are_not_cross_site(self) -> None:
        s = _settings(
            frontend_base_url="https://sstuitions.com",
            backend_base_url="https://api.sstuitions.com",
        )
        assert not s.is_cross_site

    def test_localhost_with_different_ports_is_not_cross_site(self) -> None:
        s = _settings(
            frontend_base_url="http://localhost:3000",
            backend_base_url="http://localhost:8000",
        )
        assert not s.is_cross_site


class TestProductionGuard:
    def test_valid_cross_site_config_passes(self) -> None:
        _settings().assert_production_safe()

    def test_cross_site_with_lax_cookie_is_rejected(self) -> None:
        """The exact bug that broke sign-in in development."""
        s = _settings(cookie_samesite="lax")
        with pytest.raises(RuntimeError, match="different domains"):
            s.assert_production_safe()

    def test_samesite_none_without_secure_is_rejected(self) -> None:
        s = _settings(cookie_secure=False)
        with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
            s.assert_production_safe()

    def test_weak_jwt_secret_is_rejected(self) -> None:
        s = _settings(jwt_secret="short")
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            s.assert_production_safe()

    def test_development_is_not_checked(self) -> None:
        """Local development must stay easy; the guard is production-only."""
        Settings(
            app_env="development",
            jwt_secret="short",
            cookie_secure=False,
            cookie_samesite="lax",
        ).assert_production_safe()
