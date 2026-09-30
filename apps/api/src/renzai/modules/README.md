# Backend module boundaries

Phase 4 established these package boundaries from the Phase 2 module architecture: `auth`, `users`, `organizations`, `memberships`, `applications`, `environments`, `api_keys`, `security`, `detectors`, `risk`, `policies`, `incidents`, `logs`, `providers`, `gateway`, `ai_intelligence`, `audit`, `notifications`, and `analytics`. Phases 5–8 add identity/tenancy, deterministic analysis, risk/policy, encrypted provider configuration, and the limited non-streaming Gateway within those boundaries.

Modules add `domain`, `application`, ports, infrastructure, and transport wiring only as justified. Pure domain code does not import FastAPI, SQLAlchemy, Redis, Celery, or HTTP clients. Provider and Gateway application contracts remain independent of the pinned-IP HTTP adapter; crypto, persistence, and rate limiting remain adapter concerns. Incidents, notifications, AI intelligence, analytics, and later product modules remain unimplemented boundaries.
