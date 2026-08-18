"""Push all backend environment variables to a Hugging Face Space.

Reads C:\\dev\\ss-tuitions\\.env, applies the production overrides a deployed
backend needs, and sets each value on the Space via the Hugging Face API —
non-sensitive ones as Variables, sensitive ones as Secrets.

Values are read from .env and sent straight to Hugging Face; they are never
printed. Run once:

    set HF_TOKEN=hf_your_write_token
    ./.venv/Scripts/python -m scripts.configure_hf_space

The token needs Write access. Get one at huggingface.co/settings/tokens.
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

SPACE_ID = "sstutions/ss-tuitions-api"
FRONTEND = "https://ss-tuitons.vercel.app"
BACKEND = "https://sstutions-ss-tuitions-api.hf.space"

# Keys whose value carries a credential. Everything else is a plain Variable.
SECRET_KEYS = {
    "DATABASE_URL",
    "DATABASE_DIRECT_URL",
    "JWT_SECRET",
    "MESSAGE_ENCRYPTION_KEY",
    "GEMINI_API_KEY",
    "EMAIL_SMTP_PASSWORD",
    "SUPABASE_SERVICE_ROLE_KEY",
}

# Values that differ from local development. These win over whatever is in .env.
PRODUCTION_OVERRIDES = {
    "APP_ENV": "production",
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "none",
    "FORCE_HTTPS": "true",
    "FRONTEND_BASE_URL": FRONTEND,
    "CORS_ALLOWED_ORIGINS": FRONTEND,
    "BACKEND_BASE_URL": BACKEND,
}

# The keys the deployed backend actually needs. Anything not here (Redis,
# Google Meet, Voyage, storage) is unused or has a safe default.
WANTED = [
    "APP_ENV",
    "APP_NAME",
    "APP_TIMEZONE",
    "BACKEND_BASE_URL",
    "FRONTEND_BASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
    "FORCE_HTTPS",
    "DATABASE_URL",
    "DATABASE_DIRECT_URL",
    "JWT_SECRET",
    "MESSAGE_ENCRYPTION_KEY",
    "AI_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "AI_STRIP_IDENTIFIERS",
    "EMAIL_ENABLED",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_SMTP_USER",
    "EMAIL_SMTP_PASSWORD",
    "EMAIL_FROM_ADDRESS",
    "EMAIL_FROM_NAME",
    "PAYMENT_UPI_ID",
    "PAYMENT_PAYEE_NAME",
    "PAYMENT_PHONE_NUMBER",
    "PAYMENT_BANK_NAME",
    "PAYMENT_ACCOUNT_NUMBER",
    "PAYMENT_IFSC",
    "PAYMENT_QR_IMAGE_URL",
    "PAYMENT_INSTRUCTIONS",
]


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        # Strip an inline comment only when the value is not quoted.
        values[key.strip()] = val.strip()
    return values


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("Set HF_TOKEN first. In Command Prompt:")
        print('  set HF_TOKEN=hf_your_write_token')
        print("Then run this again.")
        return 1

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        print(f"Could not find {env_path}")
        return 1

    env = load_env(env_path)
    env.update(PRODUCTION_OVERRIDES)

    api = HfApi(token=token)

    set_secret = 0
    set_var = 0
    skipped: list[str] = []

    for key in WANTED:
        value = env.get(key, "")
        if value == "" or value.upper().startswith("CONFIGURE_ME") or value.upper().startswith("CHANGE_ME"):
            skipped.append(key)
            continue
        try:
            if key in SECRET_KEYS:
                api.add_space_secret(repo_id=SPACE_ID, key=key, value=value)
                set_secret += 1
                print(f"  secret   {key}")
            else:
                api.add_space_variable(repo_id=SPACE_ID, key=key, value=value)
                set_var += 1
                print(f"  variable {key} = {value if key not in SECRET_KEYS else '***'}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED   {key}: {type(exc).__name__}: {exc}")
            return 1

    print(f"\nDone: {set_var} variables, {set_secret} secrets set on {SPACE_ID}.")
    if skipped:
        print(f"Skipped (empty/placeholder in .env): {', '.join(skipped)}")
    print("\nThe Space will rebuild automatically. Watch it turn 'Running'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
