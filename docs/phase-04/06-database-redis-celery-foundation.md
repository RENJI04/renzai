# Database, Redis and Celery foundation

SQLAlchemy uses an async engine/session maker, explicit metadata naming conventions and a unit-of-work-friendly session context. Alembic is async-compatible and imports application metadata without product schema side effects. UUIDv7 comes from `uuid6`, returns a standard Python UUID and maps to PostgreSQL `UUID` columns later.

Redis is a lazy async client with ping/close methods and no feature cache. Celery uses Redis broker/backend configuration, JSON-only accept/task/result serializers, UTC, bounded time limits and eager support for tests. Its only task is a side-effect-free correlation-ID diagnostic. PostgreSQL and Redis connectivity are documented integration paths, not claimed external-service results.
