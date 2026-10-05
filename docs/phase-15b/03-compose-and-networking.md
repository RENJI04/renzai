# Compose and networking

`compose.yaml` defines PostgreSQL, Redis, a one-shot migration job, API, worker, web, and Nginx. The `observability` profile adds PostgreSQL and Redis exporters, an OpenTelemetry Collector, Prometheus, and Grafana.

Four networks separate roles: `edge` joins Nginx and web, `application` joins proxy/web/API/worker, `data` is internal and joins only database consumers, and `observability` is internal and joins telemetry producers and collectors. PostgreSQL, Redis, Prometheus, exporters, the Collector, API, worker, and web publish no host ports. Nginx defaults to `127.0.0.1:8080`; optional Grafana defaults to `127.0.0.1:3001`.

Core startup is `docker compose --env-file deploy/.env up --build -d`. Observability startup is `docker compose --env-file deploy/.env --profile observability up --build -d`. Pass `--env-file deploy/.env` to subsequent `docker compose ps`, `logs`, `exec`, and `down` commands too: service `env_file` does not supply values for Compose interpolation. Do not add `-v` to `down` unless permanent database, Redis, Prometheus, and Grafana data deletion is explicitly intended.
