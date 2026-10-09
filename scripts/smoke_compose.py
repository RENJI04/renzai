"""Non-destructive smoke verification for an already running Renzai Compose stack."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _get(url: str, *, attempts: int = 30) -> tuple[int, bytes]:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            if error.code >= 500:
                last_error = error
                time.sleep(2)
                continue
            return error.code, error.read()
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(2)
    raise RuntimeError(f"smoke request failed for {url}: {last_error}")


def _compose(*arguments: str, env_file: str) -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker is required for Compose smoke verification")
    completed = subprocess.run(  # noqa: S603
        [docker, "compose", "--env-file", env_file, *arguments],
        cwd=ROOT,
        env={**os.environ, "RENZAI_ENV_FILE": env_file},
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--grafana-url", default="http://127.0.0.1:3001")
    parser.add_argument("--observability", action="store_true")
    parser.add_argument("--env-file", default="deploy/.env")
    args = parser.parse_args()

    health_status, health_body = _get(f"{args.base_url}/health")
    ready_status, ready_body = _get(f"{args.base_url}/ready")
    page_status, page_body = _get(args.base_url)
    session_status, _ = _get(f"{args.base_url}/api/v1/auth/session")
    if health_status != 200 or json.loads(health_body) != {"status": "ok"}:
        raise RuntimeError("API liveness response is not healthy")
    if ready_status != 200 or json.loads(ready_body).get("status") != "ready":
        raise RuntimeError("API readiness response is not ready")
    if page_status != 200 or b"Renzai" not in page_body:
        raise RuntimeError("frontend is not reachable through the reverse proxy")
    if session_status not in {200, 401}:
        raise RuntimeError("session route is not reachable")

    worker_ping = _compose(
        "exec",
        "-T",
        "renzai-worker",
        "celery",
        "-A",
        "renzai_worker.celery_app:celery_app",
        "inspect",
        "ping",
        "--timeout",
        "8",
        env_file=args.env_file,
    )
    if "pong" not in worker_ping.lower():
        raise RuntimeError("Celery worker did not answer an inspect ping")

    _compose("exec", "-T", "postgres", "pg_isready", env_file=args.env_file)
    if "PONG" not in _compose("exec", "-T", "redis", "redis-cli", "ping", env_file=args.env_file):
        raise RuntimeError("Redis did not answer PING")

    if args.observability:
        targets = _compose(
            "exec",
            "-T",
            "prometheus",
            "wget",
            "-qO-",
            "http://127.0.0.1:9090/api/v1/targets",
            env_file=args.env_file,
        )
        parsed_targets = json.loads(targets)
        health_by_job = {
            item["labels"].get("job"): item.get("health")
            for item in parsed_targets["data"]["activeTargets"]
        }
        required_jobs = {"renzai-api", "renzai-worker", "postgres", "redis", "prometheus"}
        if any(health_by_job.get(job) != "up" for job in required_jobs):
            raise RuntimeError(f"Prometheus target health is incomplete: {health_by_job}")
        grafana_status, _ = _get(f"{args.grafana_url}/api/health")
        if grafana_status != 200:
            raise RuntimeError("Grafana health endpoint is unavailable")

    print("Renzai Compose smoke verification passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"smoke verification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
