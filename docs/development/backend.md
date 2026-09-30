# Backend development

The backend uses FastAPI, Pydantic settings, SQLAlchemy async, Alembic, Redis, Celery and structlog. `renzai.app.create_app` is the testable application factory; `renzai.main:app` is the ASGI entry point. Phase 5 routes are under `/api/v1/auth`, `/api/v1/organizations`, and `/api/v1/invitations`.

Apply the Phase 5 schema with `python -m alembic upgrade head`. The application never creates schema at startup. SQLite is used only for fast isolated request tests; PostgreSQL remains the production database and validates transaction advisory locks used by the last-owner invariant.

Set a safe local `RENZAI_DATABASE_URL` before Alembic commands. Never point tests or migrations at production.
