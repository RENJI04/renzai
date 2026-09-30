# Database migrations

Revision `20260924_0001` is the Phase 5 baseline and creates ten tables, foreign keys, uniqueness rules, and indexes. Migration commands use the async URL from `RENZAI_DATABASE_URL`; schema creation is never an application-startup side effect.

The verification gate performs upgrade, Alembic metadata drift check, downgrade, and a second upgrade on an isolated database. PostgreSQL remains authoritative for UUID, transaction, row-lock, and advisory-lock behavior. The complete schema inventory and audit-event split are in [persistence and migration](05-persistence-and-migration.md).
