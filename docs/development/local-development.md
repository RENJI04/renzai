# Local development

Phase 5 supports Python 3.13+, Node.js 22+ and pnpm 11+. PostgreSQL and Redis are required for production behavior and full integration evidence; fast request tests use isolated SQLite and an in-memory rate-limit adapter.

1. Copy `.env.example` to `.env` and replace only local placeholders.
2. Create `.venv` with `python -m venv .venv`, then install `.[dev]` with `.\.venv\Scripts\python -m pip install -e ".[dev]"` on Windows.
3. Run `pnpm install --frozen-lockfile` at repository root.
4. Start the backend with `.venv\Scripts\python -m uvicorn renzai.main:app --app-dir apps/api/src --reload` on Windows, or the POSIX equivalent.
5. Start the frontend with `pnpm --dir apps/web dev`.

`GET /health` only reports whether the process is alive. `GET /ready` also verifies PostgreSQL and, in staging/production by default, Redis. It intentionally returns no dependency topology.

The root Makefile mirrors common commands but uses Windows `.venv/Scripts` paths; direct commands above are the portable source of truth for this Windows-oriented workspace.
