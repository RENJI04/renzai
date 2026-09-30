# Project structure

`apps/api/src/renzai` contains core framework primitives, async database support, HTTP composition and infrastructure adapters. `modules/` has the 19 Phase 2 package boundaries, with a boundary README instead of premature domain boilerplate. `workers/src/renzai_worker` contains Celery configuration and one diagnostic task. `apps/web` contains the Next.js shell, shared API/context/UI conventions and tests. `alembic/` has async migration wiring but no revision because there are no product tables.

Dependency direction remains transport → application → domain; adapters implement explicit ports. Domain code may not import FastAPI, SQLAlchemy, Redis, Celery or HTTP clients. The architecture test enforces package presence and scans future `domain/` files for forbidden direct imports.
