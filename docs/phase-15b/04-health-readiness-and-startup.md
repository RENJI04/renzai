# Health, readiness, and startup

`/health` is process liveness and returns only `{"status":"ok"}`. `/ready` verifies the database and, when configured as required, Redis. It reveals only a ready/unavailable result and never DSNs or topology. Optional AI providers and observability backends do not gate global readiness.

Compose waits for PostgreSQL and Redis health, runs exactly one migration service, then starts API and worker after the migration exits successfully. The API container health check uses `/ready`; web waits for API readiness, and Nginx waits for web health and API readiness. This avoids sleep-based ordering and multi-replica migration races.

The worker container health check uses Celery control ping through Redis. A healthy process is not proof that all optional providers are available. If migrations fail, API and worker stay stopped; inspect `docker compose --env-file deploy/.env logs migrate`, correct configuration or migration inputs, and rerun without modifying historical migration files.
