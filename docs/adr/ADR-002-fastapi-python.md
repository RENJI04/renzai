# ADR-002: Python and FastAPI backend

**Status:** Accepted for Phase 2 architecture

## Context

V1 needs documented APIs, bounded validation, independent security-engine tests and async provider/database I/O.

## Decision

Use Python, FastAPI and Pydantic at the transport boundary; SQLAlchemy async for persistence and Alembic for later migration management. Domain rules remain framework independent.

## Alternatives considered

Node/TypeScript could share language with the frontend but would require a separate choice of validation and Python-friendly security tooling. A synchronous Python stack is simpler but can tie up workers during provider I/O. No framework is assumed to supply authorization automatically.

## Consequences

Explicit dependency injection and async session lifecycle are required. FastAPI-generated OpenAPI is reviewed against actual behavior. Python CPU-heavy detectors may need measurement and worker/process strategies before extraction.

## Security implications

Pydantic validation is one boundary, not a substitute for tenant authorization, payload limits, query parameterization or safe errors.

## Requirement references

FR-020–021, FR-054–055; NFR-001, NFR-010, NFR-014–015; SEC-004, SEC-007–008; US-007, US-032.
