# Backend foundation

`create_app(settings)` configures the FastAPI factory without network work at import time. Its lifespan creates lazy runtime dependencies and disposes them on shutdown. `/health` is liveness only; `/ready` validates the database and conditionally Redis without exposing topology. OpenAPI identifies a Phase 4 foundation, and docs are configurable/off by default in production.

The error model implements the Phase 3 envelope and stable code classes, although feature routes do not yet raise most of them. `X-Request-ID` accepts only bounded safe IDs or creates a UUID, appears in responses and structured logs, and is held in a `ContextVar`.
