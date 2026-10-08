# Troubleshooting

Start with `docker compose --env-file <file> ps`, bounded service logs, `/health`, and `/ready`. Never
paste secrets, cookies, API keys, prompts, or provider responses into an issue.

| Symptom | Checks and safe recovery |
| --- | --- |
| Docker engine unavailable | Start Docker Desktop/Engine; verify `docker info` and `docker run --rm hello-world`. On Windows confirm WSL 2 integration is enabled. |
| Docker disk/storage exhausted | Stop writers, inspect `docker system df`, relocate/expand Docker storage or remove only known disposable objects. Preserve named volumes; do not run broad deletion commands. |
| PostgreSQL connection refused | Check `postgres` health, the configured async URL, URL-encoded password, network membership, and volume/disk health. Do not edit a migration to force startup. |
| Redis unavailable | Check `redis-cli ping`, AOF volume, and network. Security-required session/limiter paths intentionally fail closed in production. |
| Migrations not applied | Inspect the one-shot `migrate` service and run `alembic current`. Correct configuration/data, then rerun; never modify historical migrations. |
| Port already in use | Change `RENZAI_HTTP_PORT` or `RENZAI_GRAFANA_PORT` in the selected untracked env file; keep loopback binding for local evaluation. |
| Frontend/API rewrite fails | Confirm Nginx, web, and API are healthy and share the declared networks; verify `/health`, `/api/v1/health`, and the Next.js API origin. |
| Local session does not persist | Production config requires HTTPS and secure cookies. Use the explicit local `compose.demo.yaml` path for HTTP loopback; do not weaken production settings. |
| CSRF error | Bootstrap `GET /api/v1/auth/session`, retain its cookie, send the exact `X-Renzai-CSRF` value and same-origin `Origin`; refresh after login/password changes. |
| Rate-limit response | Wait for the bounded window and fix request loops. Do not disable production Redis or limiters. Attack Lab should be run at a deliberate pace. |
| Worker unavailable | Check Redis, worker health, and a bounded Celery ping. Restart after dependencies; duplicate-delivery and claim protections remain authoritative. |
| Provider unavailable | Validate configured URL/credential from the UI, DNS/network policy, timeout and response size. Deterministic Analyze remains independent; Gateway fails safely. |
| Prometheus target down | Inspect `http://prometheus:9090/api/v1/targets` inside the network and the corresponding service/exporter health. Do not expose internal ports as a shortcut. |
| Grafana does not start | Check the loopback management port, Grafana volume permissions, generated admin value, datasource and dashboard provisioning logs. Grafana must not receive application secrets. |
| OTel Collector issue | Validate `infrastructure/otel/collector.yaml`, Collector health/metrics, endpoint scheme, and allowlisted exporter. Batch export is not enforcement authority. |
| Disk full | Stop writers, preserve database/Redis volumes, expand or carefully reclaim storage, then validate data stores before resuming. |
| Windows/WSL path issue | Run commands from the repository drive visible to Docker, use PowerShell path syntax where shown, and avoid copying Linux ownership assumptions to Windows. |
| pnpm install/build-policy failure | Use the pinned pnpm version and `pnpm install --frozen-lockfile`. The workspace intentionally denies the `unrs-resolver` postinstall script; do not approve scripts casually. |

For production recovery boundaries see [Phase 15B recovery](phase-15b/11-backup-recovery-and-troubleshooting.md).
