"""Static safety checks for the Phase 15B deployment assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def verify() -> list[str]:
    errors: list[str] = []
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    nginx = (ROOT / "infrastructure/nginx/renzai.conf").read_text(encoding="utf-8")
    prometheus = (ROOT / "infrastructure/prometheus/prometheus.yml").read_text(encoding="utf-8")
    collector = (ROOT / "infrastructure/otel/collector.yaml").read_text(encoding="utf-8")

    for service in ("postgres", "redis", "prometheus", "otel-collector"):
        block = _service_block(compose, service)
        if "ports:" in block:
            errors.append(f"{service} must not publish host ports")
    for service in ("renzai-api", "renzai-worker", "renzai-web", "nginx"):
        block = _service_block(compose, service)
        if "cap_drop: [ALL]" not in block:
            errors.append(f"{service} must drop Linux capabilities")
        if "no-new-privileges:true" not in block:
            errors.append(f"{service} must set no-new-privileges")
    if "127.0.0.1" not in _service_block(compose, "nginx"):
        errors.append("nginx must default to a loopback host binding")
    if "proxy_set_header X-Request-ID" not in nginx:
        errors.append("nginx must propagate the bounded request identifier")
    if "proxy_set_header X-Forwarded-Proto $scheme" not in nginx:
        errors.append("nginx must author the forwarded protocol")
    if "proxy_set_header X-Forwarded-For $remote_addr" not in nginx:
        errors.append("nginx must replace untrusted forwarded client addresses")
    if '"~^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"' not in nginx:
        errors.append("nginx request-id regex containing braces must be quoted")
    if "env_file:" in _service_block(compose, "grafana"):
        errors.append("Grafana must not receive the application deployment env file")
    if "networks: [observability, management]" not in _service_block(compose, "grafana"):
        errors.append("Grafana loopback publication requires its isolated management network")
    if "--web.enable-lifecycle" in _service_block(compose, "prometheus"):
        errors.append("Prometheus runtime reload must remain disabled")
    api_dockerfile = (ROOT / "infrastructure/docker/Dockerfile.api").read_text(encoding="utf-8")
    worker_dockerfile = (ROOT / "infrastructure/docker/Dockerfile.worker").read_text(
        encoding="utf-8"
    )
    if "8000/ready" not in api_dockerfile:
        errors.append("API container health must verify readiness")
    if "HEALTHCHECK --interval=20s --timeout=15s" not in worker_dockerfile:
        errors.append("worker container health must allow the bounded Celery ping to finish")
    if "/metrics" not in prometheus or "renzai-api:8000" not in prometheus:
        errors.append("Prometheus must scrape the internal API metrics endpoint")
    if "host: 0.0.0.0" not in collector or "port: 8888" not in collector:
        errors.append("Collector internal metrics must bind to the observability network")
    if "address: 0.0.0.0:8888" in collector:
        errors.append("Collector must not use the ignored legacy metrics address setting")

    dashboard_path = ROOT / "infrastructure/grafana/dashboards/renzai-platform-overview.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    if dashboard.get("title") != "Renzai Platform Overview":
        errors.append("Grafana platform dashboard is missing or misnamed")
    expressions = " ".join(
        target.get("expr", "")
        for panel in dashboard.get("panels", [])
        for target in panel.get("targets", [])
    )
    forbidden_labels = ("request_id", "email", "user_id", "organization_id", "prompt")
    for label in forbidden_labels:
        if label in expressions:
            errors.append(f"Grafana query uses forbidden high-cardinality label: {label}")
    return errors


def _service_block(compose: str, service: str) -> str:
    marker = f"  {service}:\n"
    try:
        start = compose.index(marker) + len(marker)
    except ValueError:
        return ""
    next_service = re.search(r"(?m)^  [A-Za-z0-9_-]+:\s*$", compose[start:])
    return (
        compose[start:] if next_service is None else compose[start : start + next_service.start()]
    )


def main() -> int:
    errors = verify()
    if errors:
        for error in errors:
            print(f"Phase 15B asset error: {error}", file=sys.stderr)
        return 1
    print("Phase 15B deployment assets verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
