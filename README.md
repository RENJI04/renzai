# Renzai

**Open-Source AI Security & Observability Platform**

Renzai is a self-hostable platform for analyzing and governing LLM-application traffic. It provides explainable, deterministic security detection, risk scoring, policy decisions, incident investigation, privacy-safe operational analytics, and optional advisory AI incident intelligence. Renzai is currently at **Phase 11 AI intelligence implementation**.

## Goals and principles

- Secure by default. AI optional. Explainable by design.
- Keep core security useful without an external AI provider.
- Support direct analysis APIs and an AI gateway.
- Respect privacy-aware storage and self-hosted deployment needs.
- Begin as a modular monolith when implementation starts.

## Roadmap

Phases 1–3 define product, architecture, and contracts; Phases 4–10 implement the deterministic platform, Gateway, incidents, and analytics; Phase 11 adds optional asynchronous AI-generated incident summaries, explanations, mitigations, and validated policy drafts. Notifications, webhooks, SDKs, agents, and advanced provider protocol features remain later work.

## Documentation

The authoritative product baseline is in [Phase 1](docs/phase-01/12-phase-01-review.md). The V1 design is in [Phase 2](docs/phase-02/01-architecture-overview.md), and its logical contracts are in [Phase 3](docs/phase-03/21-phase-03-review.md). Implementation reviews cover [Phase 4](docs/phase-04/10-phase-04-review.md), [Phase 5](docs/phase-05/10-phase-05-review.md), [Phase 6](docs/phase-06/10-phase-06-review.md), [Phase 7](docs/phase-07/10-phase-07-review.md), [Phase 8](docs/phase-08/10-phase-08-review.md), [Phase 9](docs/phase-09/10-phase-09-review.md), [Phase 10](docs/phase-10/10-phase-10-review.md), and [Phase 11](docs/phase-11/10-phase-11-review.md).

## Implemented platform boundary

Phase 11 includes the prior deterministic platform plus purpose-separated AI provider configuration, ID-only asynchronous jobs, privacy-approved incident context, strictly validated AI results, and a labelled Incident UI. AI remains advisory and optional; it cannot change findings, risk, policies, incidents, or Gateway decisions. Renzai still does **not** implement streaming, tools/functions, multimodal input, full OpenAI parity, notifications, webhooks, autonomous remediation, SDKs, or agents.

## Repository layout

- `apps/api` — FastAPI identity/tenancy, deterministic analysis, provider/Gateway, incidents, analytics, and optional AI intelligence backend.
- `apps/web` — Next.js management console, operational dashboard, Security Playground, policy/provider UI, and Incident Queue.
- `workers` — JSON-only Celery bootstrap, diagnostics, and ID-only AI intelligence task.
- `docs/phase-11` — AI architecture, privacy, task contracts, security, traceability, and review.
- `docs/development` — local setup and command reference.

## Local development

Prerequisites: Python 3.13+, Node.js 22+, pnpm 11+, PostgreSQL and Redis for full readiness checks. Copy `.env.example` to `.env` and replace only local placeholders. Use the raw commands below on Windows if `make` is unavailable:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
.\.venv\Scripts\python -m uvicorn renzai.main:app --app-dir apps/api/src --reload
pnpm --dir apps/web dev
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

See [local development](docs/development/local-development.md) for setup, [configuration](docs/development/configuration.md) for environment rules, and [testing](docs/development/testing.md) for what is and is not an integration check.
