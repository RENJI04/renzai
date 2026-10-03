"""Run Phase 12 SDKs against an ephemeral local Renzai HTTP server."""

from __future__ import annotations

import asyncio
import json
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
for source in (ROOT / "apps/api/src", ROOT / "packages/python-sdk/src"):
    sys.path.insert(0, str(source))

from renzai_sdk import ConfigurationError, Renzai, RenzaiSession  # noqa: E402

from renzai.app import create_app  # noqa: E402
from renzai.core.config import Environment, Settings  # noqa: E402
from renzai.db import models as _models  # noqa: E402, F401
from renzai.db.base import Base  # noqa: E402
from renzai.db.session import Database  # noqa: E402


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _required(response: httpx.Response, status: int) -> dict[str, object]:
    if response.status_code != status:
        raise RuntimeError(f"local API returned {response.status_code}: {response.text[:500]}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("local API returned a non-object")
    return payload


def _bootstrap(client: httpx.Client) -> tuple[str, str, str, str, str]:
    _required(
        client.post(
            "/api/v1/auth/register",
            json={"email": "phase12@example.com", "password": "correct horse phase 12"},
        ),
        201,
    )
    session = _required(client.get("/api/v1/auth/session"), 200)
    csrf = str(session["csrf_token"])
    headers = {"X-Renzai-CSRF": csrf}
    organization = _required(
        client.post(
            "/api/v1/organizations",
            headers=headers,
            json={"name": "Phase Twelve", "slug": "phase-twelve"},
        ),
        201,
    )
    organization_id = str(organization["organization_id"])
    application = _required(
        client.post(
            f"/api/v1/organizations/{organization_id}/applications",
            headers=headers,
            json={"name": "SDK compatibility"},
        ),
        201,
    )
    application_id = str(application["application_id"])
    environment = _required(
        client.post(
            f"/api/v1/organizations/{organization_id}/applications/{application_id}/environments",
            headers=headers,
            json={"type": "development"},
        ),
        201,
    )
    environment_id = str(environment["environment_id"])
    key = _required(
        client.post(
            f"/api/v1/organizations/{organization_id}/applications/{application_id}/"
            f"environments/{environment_id}/keys",
            headers=headers,
            json={"label": "phase12-local"},
        ),
        201,
    )
    return organization_id, application_id, environment_id, csrf, str(key["secret_once"])


async def _create_schema(settings: Settings) -> None:
    database = Database(settings.database)
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await database.close()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="renzai-phase12-") as directory:
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        database_path = Path(directory) / "compatibility.sqlite3"
        settings = Settings(
            app_environment=Environment.TEST,
            app_public_base_url=base_url,
            database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
            session_secure_cookie=False,
            auth_rate_limit_attempts=100,
            analyze_rate_limit_requests=100,
            gateway_rate_limit_requests=100,
            outbound_trusted_local_provider_hosts=("127.0.0.1",),
        )
        asyncio.run(_create_schema(settings))
        app = create_app(settings)
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("local Renzai server did not start")

        try:
            with httpx.Client(base_url=base_url, timeout=10) as bootstrap_client:
                organization_id, application_id, environment_id, csrf, api_key = _bootstrap(
                    bootstrap_client
                )
                incident = _required(
                    bootstrap_client.post(
                        f"/api/v1/organizations/{organization_id}/incidents",
                        headers={"X-Renzai-CSRF": csrf, "Idempotency-Key": "phase12-local"},
                        json={
                            "title": "SDK compatibility incident",
                            "severity": "medium",
                            "safe_summary": "Safe synthetic summary.",
                        },
                    ),
                    201,
                )
                session_token = bootstrap_client.cookies.get("renzai_session")
                if session_token is None:
                    raise RuntimeError("local session cookie was not issued")

                with Renzai(api_key=api_key, base_url=base_url) as client:
                    analysis = client.analyze(content="Safe synthetic example", direction="input")
                    if not analysis.request_id or not analysis.analysis_id:
                        raise RuntimeError("Python Analyze omitted identifiers")
                    try:
                        client.gateway.create(
                            model="safe-model",
                            messages=[],
                        )
                    except ValueError:
                        pass
                    else:
                        raise RuntimeError("Python Gateway accepted an empty message list")
                    try:
                        from renzai_sdk import ChatMessage

                        client.gateway.create(
                            model="safe-model",
                            messages=[ChatMessage(role="user", content="Safe synthetic example")],
                        )
                    except ConfigurationError:
                        pass
                    else:
                        raise RuntimeError(
                            "Gateway without a provider did not return configuration_error"
                        )

                with RenzaiSession(
                    session_token=session_token,
                    csrf_token=csrf,
                    cookie_name="renzai_session",
                    base_url=base_url,
                ) as session_client:
                    loaded = session_client.get_incident(
                        organization_id, str(incident["incident_id"])
                    )
                    if loaded.incident_id != str(incident["incident_id"]):
                        raise RuntimeError("Python incident read returned the wrong incident")

            module_url = (ROOT / "packages/typescript-sdk/dist/index.js").resolve().as_uri()
            node_program = f"""
import {{ ConfigurationError, Renzai, RenzaiSession }} from {json.dumps(module_url)};
const client = new Renzai({{
  apiKey: process.env.RENZAI_API_KEY,
  baseUrl: process.env.RENZAI_BASE_URL,
}});
const analysis = await client.analyze({{
  content: "Safe synthetic example",
  direction: "input",
}});
if (!analysis.requestId || !analysis.analysisId) {{
  throw new Error("TypeScript Analyze omitted identifiers");
}}
let gatewayFailedSafely = false;
try {{
  await client.gateway.create({{
    model: "safe-model",
    messages: [{{ role: "user", content: "Safe synthetic example" }}],
  }});
}} catch (error) {{ gatewayFailedSafely = error instanceof ConfigurationError; }}
if (!gatewayFailedSafely) throw new Error("Gateway did not return configuration_error");
const session = new RenzaiSession({{
  sessionToken: process.env.RENZAI_SESSION_TOKEN,
  csrfToken: process.env.RENZAI_CSRF_TOKEN,
  cookieName: "renzai_session",
  baseUrl: process.env.RENZAI_BASE_URL,
}});
const incident = await session.getIncident(
  process.env.RENZAI_ORGANIZATION_ID,
  process.env.RENZAI_INCIDENT_ID,
);
if (incident.incidentId !== process.env.RENZAI_INCIDENT_ID) {{
  throw new Error("TypeScript incident mismatch");
}}
console.log(JSON.stringify({{ analyze: "ok", gatewayError: "ok", incident: "ok" }}));
"""
            environment = {
                **os.environ,
                "RENZAI_BASE_URL": base_url,
                "RENZAI_API_KEY": api_key,
                "RENZAI_SESSION_TOKEN": session_token,
                "RENZAI_CSRF_TOKEN": csrf,
                "RENZAI_ORGANIZATION_ID": organization_id,
                "RENZAI_INCIDENT_ID": str(incident["incident_id"]),
            }
            node_path = shutil.which("node")
            if node_path is None:
                raise RuntimeError("Node.js is required for the TypeScript compatibility check")
            completed = subprocess.run(  # noqa: S603 - fixed local Node executable and test input
                [node_path, "--input-type=module", "--eval", node_program],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            print(
                json.dumps(
                    {
                        "python_analyze": "ok",
                        "python_gateway_error": "ok",
                        "python_incident": "ok",
                        "typescript": json.loads(completed.stdout),
                    }
                )
            )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("local Renzai server did not stop")


if __name__ == "__main__":
    main()
