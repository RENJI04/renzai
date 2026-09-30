# ADR-003: Next.js and TypeScript frontend

**Status:** Accepted for Phase 2 architecture

## Context

The dashboard needs authenticated workflows, charts, incident detail and form-heavy configuration for modern browsers.

## Decision

Use Next.js, React and TypeScript, with Tailwind CSS, shadcn/ui, TanStack Query and Recharts. Server-rendered route shells establish initial session/context; client components handle interactive flows.

## Alternatives considered

A client-only SPA reduces server-rendering complexity but shifts more initial data flow to browser fetches. A server-template UI could be smaller but is less suited to rich incident/playground interaction. UI technology does not change backend authority.

## Consequences

Keep feature-based folders and tenant-partitioned query caches. Review server/client data serialization to avoid leaking one-time keys or provider secrets.

## Security implications

Server-side RBAC, CSRF, output encoding and safe caching are mandatory; hidden controls in the UI grant no permission.

## Requirement references

FR-039–040, FR-043, FR-051–053; NFR-012; SEC-004–005, SEC-009; US-018, US-020, US-024.
