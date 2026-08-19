"""Application settings, loaded from environment. See .env.example at repo root."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Core ----
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "SS Tuitions"
    app_timezone: str = "Asia/Kolkata"
    backend_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    # ---- Database ----
    # DATABASE_URL drives the app (async); DATABASE_DIRECT_URL drives Alembic (sync).
    database_url: str = ""
    database_direct_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # True on Vercel/Lambda-style hosting: use NullPool and disable
    # asyncpg prepared statements, which a transaction pooler cannot
    # support. Set SERVERLESS=true in that environment.
    serverless: bool = False

    # ---- Auth ----
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # ---- Messaging ----
    # AES-256-GCM key for message bodies at rest. The server can decrypt, by
    # design, so admins can review conversations for child safety. This is NOT
    # end-to-end encryption and must never be described as such.
    message_encryption_key: str = ""

    # ---- Redis / rate limiting ----
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_login_per_minute: int = 5
    rate_limit_api_per_minute: int = 120

    # ---- Storage ----
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    storage_bucket_content: str = "ss-content"
    storage_bucket_submissions: str = "ss-submissions"
    storage_max_upload_mb: int = 25
    storage_signed_url_ttl_seconds: int = 300

    # ---- AI ----
    # "gemini" = Google AI Studio free tier (1,500 requests/day, no card).
    # "anthropic" = Claude, paid. Empty disables all AI features cleanly.
    ai_provider: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    anthropic_api_key: str = ""
    ai_model_tutor: str = "claude-sonnet-5"
    ai_model_question_gen: str = "claude-opus-5"
    ai_model_vision: str = "claude-sonnet-5"

    voyage_api_key: str = ""
    embedding_dimensions: int = 1024

    # Students are minors and free tiers may train on submitted data, so
    # identifiers are stripped before anything is sent. Turning this off is a
    # deliberate act, not an accident.
    ai_strip_identifiers: bool = True
    ai_daily_message_limit_per_student: int = 40

    # ---- Google Meet (inactive until Workspace is available) ----
    google_integration_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""

    # ---- Email ----
    # "brevo" sends over HTTPS; "smtp" opens a direct SMTP connection.
    #
    # This is not a style preference. Render's free web services block outbound
    # traffic on ports 25, 465 and 587, so SMTP fails there with
    # "[Errno 101] Network is unreachable" however correct the Gmail App
    # Password is. An HTTP API goes out over 443 and is unaffected.
    email_provider: Literal["smtp", "brevo"] = "smtp"

    email_enabled: bool = False
    email_from_address: str = ""
    email_from_name: str = "SS Tuitions"

    # Used when email_provider is "brevo".
    brevo_api_key: str = ""

    # Used when email_provider is "smtp" (fine locally, blocked on Render free).
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""

    # ---- Payments (manual UPI/QR verification; no gateway) ----
    # Blank until the owner supplies them. Nothing is invented: the parent-facing
    # page shows "payment details not set up yet" rather than a wrong UPI id.
    payment_upi_id: str = ""
    payment_payee_name: str = ""
    payment_bank_name: str = ""
    payment_account_number: str = ""
    payment_ifsc: str = ""
    payment_phone_number: str = ""
    payment_qr_image_url: str = ""
    payment_instructions: str = ""

    # ---- Security ----
    cors_allowed_origins: str = "http://localhost:3000"
    audit_log_enabled: bool = True
    force_https: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_cross_site(self) -> bool:
        """True when the website and API sit on different sites.

        Browsers compare registrable domain, not port. Vercel + Render is
        cross-site; ss-tuitions.com + api.ss-tuitions.com is not.

        This matters because a SameSite=lax cookie is NOT sent on cross-site
        requests: login succeeds, then the session cannot be restored and the
        user bounces back to the login page. That exact bug appeared in
        development when the frontend called 127.0.0.1 from localhost.
        """
        from urllib.parse import urlparse

        def registrable(url: str) -> str:
            host = urlparse(url).hostname or ""
            parts = host.split(".")
            return ".".join(parts[-2:]) if len(parts) >= 2 else host

        return registrable(self.frontend_base_url) != registrable(
            self.backend_base_url
        )

    def assert_production_safe(self) -> None:
        """Fail fast rather than boot production with development defaults."""
        if not self.is_production:
            return
        problems: list[str] = []

        # A cross-site deployment needs SameSite=none, and browsers reject
        # SameSite=none unless the cookie is also Secure. Booting without this
        # produces a login that appears to work and then silently fails.
        if self.is_cross_site and self.cookie_samesite != "none":
            problems.append(
                "The website and API are on different domains, so "
                "COOKIE_SAMESITE must be 'none' or sign-in will not persist"
            )
        if self.cookie_samesite == "none" and not self.cookie_secure:
            problems.append(
                "COOKIE_SAMESITE=none requires COOKIE_SECURE=true; browsers "
                "reject the cookie otherwise"
            )
        if len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be at least 32 characters in production")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if not self.force_https:
            problems.append("FORCE_HTTPS must be true in production")
        if problems:
            raise RuntimeError("Unsafe production config: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
