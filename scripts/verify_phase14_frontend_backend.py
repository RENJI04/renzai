"""Verify the real Next rewrite and local Renzai API with synthetic data on free ports."""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

from renzai.app import create_app  # noqa: E402
from renzai.core.config import Environment, Settings  # noqa: E402
from renzai.db import models as _models  # noqa: E402, F401
from renzai.db.base import Base  # noqa: E402
from renzai.db.session import Database  # noqa: E402


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


async def create_schema(settings: Settings) -> None:
    database = Database(settings.database)
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await database.close()


def wait_for_http(url: str, process: subprocess.Popen[str] | None = None) -> None:
    deadline = time.monotonic() + (90 if process is not None else 30)
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            output = process.communicate(timeout=1)[0]
            raise RuntimeError(f"frontend server exited early: {output[-2000:]}")
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"timed out waiting for {url}")


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        process.communicate(timeout=5)
        return
    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill is None:
            raise RuntimeError("taskkill is required to stop the Windows frontend process tree")
        subprocess.run(  # noqa: S603 - exact PID created by this process
            [taskkill, "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)


def required(response: httpx.Response, status: int) -> dict[str, object]:
    if response.status_code != status:
        raise RuntimeError(f"expected {status}, got {response.status_code}: {response.text[:500]}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("expected an object response")
    return payload


def main() -> None:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required")
    with tempfile.TemporaryDirectory(prefix="renzai-phase14-web-") as directory:
        api_port, web_port = free_port(), free_port()
        api_url = f"http://127.0.0.1:{api_port}"
        web_url = f"http://127.0.0.1:{web_port}"
        settings = Settings(
            app_environment=Environment.TEST,
            app_public_base_url=web_url,
            database_url=f"sqlite+aiosqlite:///{(Path(directory) / 'frontend.sqlite3').as_posix()}",
            session_secure_cookie=False,
            auth_rate_limit_attempts=100,
            session_rate_limit_requests=100,
        )
        asyncio.run(create_schema(settings))
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(settings), host="127.0.0.1", port=api_port, log_level="warning"
            )
        )
        api_thread = threading.Thread(target=server.run, daemon=True)
        api_thread.start()
        wait_for_http(f"{api_url}/health")

        environment = {**os.environ, "RENZAI_API_ORIGIN": api_url}
        frontend = subprocess.Popen(  # noqa: S603 - fixed local package-manager command
            [pnpm, "--dir", "apps/web", "dev", "--hostname", "127.0.0.1", "--port", str(web_port)],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_for_http(web_url, frontend)
            with httpx.Client(base_url=web_url, timeout=10) as client:
                home = client.get("/")
                if home.status_code != 200 or "Renzai" not in home.text:
                    raise RuntimeError("Next frontend did not render the Renzai shell")
                required(
                    client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": "frontend-e2e@example.test",
                            "password": "correct horse phase 14",
                        },
                    ),
                    201,
                )
                session = required(client.get("/api/v1/auth/session"), 200)
                organization = required(
                    client.post(
                        "/api/v1/organizations",
                        headers={"X-Renzai-CSRF": str(session["csrf_token"])},
                        json={"name": "Frontend E2E", "slug": "frontend-e2e"},
                    ),
                    201,
                )
                listed = required(client.get("/api/v1/organizations"), 200)
                items = listed.get("items")
                if not isinstance(items, list) or not any(
                    item.get("organization_id") == organization["organization_id"]
                    for item in items
                    if isinstance(item, dict)
                ):
                    raise RuntimeError("same-origin frontend/API workflow lost organization state")
                print(
                    {
                        "frontend": "ok",
                        "rewrite": "ok",
                        "session_cookie": "ok",
                        "csrf_write": "ok",
                        "organization_read": "ok",
                    }
                )
        finally:
            stop_process_tree(frontend)
            server.should_exit = True
            api_thread.join(timeout=10)
            if api_thread.is_alive():
                raise RuntimeError("local API server did not stop")


if __name__ == "__main__":
    main()
