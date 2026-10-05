"""Fail before migrations when deployment settings still contain placeholders."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

REQUIRED_SECRETS = (
    "POSTGRES_PASSWORD",
    "RENZAI_SESSION_VERIFIER_KEY",
    "RENZAI_APPLICATION_KEY_VERIFIER_KEY",
    "RENZAI_PROVIDER_CREDENTIAL_KEYS",
)


def validate(environment: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_SECRETS:
        value = environment.get(name, "")
        if not value or "replace-" in value.lower() or "development-only" in value.lower():
            errors.append(f"{name} must be supplied through deployment secret injection")

    database_url = environment.get("RENZAI_DATABASE_URL", "")
    if not database_url.startswith("postgresql+asyncpg://") or "replace-" in database_url.lower():
        errors.append("RENZAI_DATABASE_URL must be a configured async PostgreSQL URL")

    public_url = environment.get("RENZAI_APP_PUBLIC_BASE_URL", "")
    parsed_public = urlsplit(public_url)
    if parsed_public.scheme != "https" or not parsed_public.hostname:
        errors.append("RENZAI_APP_PUBLIC_BASE_URL must be an HTTPS deployment URL")

    if environment.get("RENZAI_SESSION_SECURE_COOKIE", "").lower() != "true":
        errors.append("RENZAI_SESSION_SECURE_COOKIE must be true")
    if environment.get("RENZAI_LOGGING_JSON", "").lower() != "true":
        errors.append("RENZAI_LOGGING_JSON must be true")

    grafana_password = environment.get("GF_SECURITY_ADMIN_PASSWORD")
    if grafana_password is not None and (
        not grafana_password or "replace-" in grafana_password.lower()
    ):
        errors.append("GF_SECURITY_ADMIN_PASSWORD must be replaced before deployment")
    return errors


def main() -> int:
    errors = validate(dict(os.environ))
    if errors:
        for error in errors:
            print(f"deployment configuration error: {error}", file=sys.stderr)
        return 1
    print("deployment configuration validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
