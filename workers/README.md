# Worker foundation

`renzai_worker` contains JSON-only Celery configuration, a side-effect-free diagnostic task, and the
Phase 11 AI intelligence processor. The AI task accepts only organization/request UUID strings,
re-fetches tenant-scoped state, claims pending work atomically, and does not retry provider work.
Webhook, retention, and notification jobs remain deferred. Worker entry points set
`PYTHONPATH=apps/api/src;workers/src` on Windows or the equivalent shell path on POSIX.

`workers/tests/test_celery.py` verifies serializer configuration, bounded task defaults, UUID-only
arguments, and duplicate delivery behavior. Live single-owner/result behavior is selected with
`pytest -m "postgresql and concurrency"` when `RENZAI_TEST_DATABASE_URL` points to a disposable
PostgreSQL database.
