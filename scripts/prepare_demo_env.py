"""Create an untracked, random local-demo environment for the Compose quick start."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parents[1]
DEFAULT_PATH = ROOT / "deploy" / ".env.demo"


def render_demo_environment() -> str:
    database_password = secrets.token_urlsafe(36)
    values = {
        "COMPOSE_PROJECT_NAME": "renzai-demo",
        "RENZAI_HTTP_BIND": "127.0.0.1",
        "RENZAI_HTTP_PORT": "8080",
        "RENZAI_GRAFANA_BIND": "127.0.0.1",
        "RENZAI_GRAFANA_PORT": "3001",
        "POSTGRES_DB": "renzai_demo",
        "POSTGRES_USER": "renzai_demo",
        "POSTGRES_PASSWORD": database_password,
        "RENZAI_DATABASE_URL": (
            "postgresql+asyncpg://renzai_demo:"
            f"{quote(database_password, safe='')}@postgres:5432/renzai_demo"
        ),
        "RENZAI_DATABASE_POOL_SIZE": "5",
        "RENZAI_DATABASE_MAX_OVERFLOW": "5",
        "RENZAI_REDIS_URL": "redis://redis:6379/0",
        "RENZAI_REDIS_REQUIRED_FOR_READINESS": "true",
        "RENZAI_APP_ENVIRONMENT": "development",
        "RENZAI_APP_DEBUG": "false",
        "RENZAI_APP_PUBLIC_BASE_URL": "http://localhost:8080",
        "RENZAI_APP_TRUSTED_PROXIES": '["172.16.0.0/12"]',
        "RENZAI_FORWARDED_ALLOW_IPS": "172.16.0.0/12",
        "RENZAI_APP_EXPOSE_DOCS": "true",
        "RENZAI_CORS_ORIGINS": '["http://localhost:8080"]',
        "RENZAI_CORS_ALLOW_CREDENTIALS": "true",
        "RENZAI_LOGGING_LEVEL": "INFO",
        "RENZAI_LOGGING_JSON": "false",
        "RENZAI_SESSION_VERIFIER_KEY": secrets.token_urlsafe(48),
        "RENZAI_SESSION_VERIFIER_KEY_ID": "demo-v1",
        "RENZAI_SESSION_SECURE_COOKIE": "false",
        "RENZAI_APPLICATION_KEY_VERIFIER_KEY": secrets.token_urlsafe(48),
        "RENZAI_APPLICATION_KEY_VERIFIER_KEY_ID": "demo-v1",
        "RENZAI_PROVIDER_CREDENTIAL_ACTIVE_KEY_ID": "demo-v1",
        "RENZAI_PROVIDER_CREDENTIAL_KEYS": json.dumps(
            {"demo-v1": secrets.token_urlsafe(48)}, separators=(",", ":")
        ),
        "RENZAI_OUTBOUND_TRUSTED_LOCAL_PROVIDER_HOSTS": "[]",
        "RENZAI_FEATURE_FLAGS_UNSAFE_INSPECTION_OVERRIDE": "false",
        "RENZAI_CELERY_TASK_ALWAYS_EAGER": "false",
        "RENZAI_OBSERVABILITY_METRICS_ENABLED": "true",
        "RENZAI_OBSERVABILITY_METRICS_PATH": "/metrics",
        "RENZAI_OBSERVABILITY_TRACING_ENABLED": "false",
        "RENZAI_OBSERVABILITY_SERVICE_NAME": "renzai-api",
        "RENZAI_OBSERVABILITY_OTLP_TRACES_ENDPOINT": ("http://otel-collector:4318/v1/traces"),
        "RENZAI_OBSERVABILITY_TRACE_SAMPLE_RATIO": "0.05",
        "RENZAI_OBSERVABILITY_WORKER_METRICS_PORT": "9108",
        "GF_SECURITY_ADMIN_USER": "demo-admin",
        "GF_SECURITY_ADMIN_PASSWORD": secrets.token_urlsafe(36),
        "GF_USERS_ALLOW_SIGN_UP": "false",
    }
    return "\n".join(f"{name}={value}" for name, value in values.items()) + "\n"


def create_demo_environment(path: Path, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; use --force to rotate local values")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_demo_environment())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    try:
        create_demo_environment(arguments.output.resolve(), force=arguments.force)
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(f"Created local demo environment at {arguments.output}")
    print("The file is ignored by Git. Do not reuse its values outside local evaluation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
