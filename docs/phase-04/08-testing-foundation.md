# Testing foundation

The backend pytest suite covers only implemented foundation behavior. It uses an isolated SQLite async smoke test and readiness doubles, so it never needs a developer's production service. Redis/PostgreSQL external connectivity is available for separately configured `integration` runs. The worker check verifies JSON-safe Celery configuration and the harmless diagnostic task.

Frontend Vitest covers landing-page honesty and the error parser; Playwright configuration is present but no browser scenario is necessary for the single static foundation page. Lint, formatting, mypy, TypeScript strictness and Next production build complete the Phase 4 quality gate.
