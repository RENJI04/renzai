# ADR-004: PostgreSQL as durable store

**Status:** Accepted for Phase 2 architecture

## Context

V1 needs tenant-scoped transactional state, incidents, audit history, configuration and durable outbox intents.

## Decision

Use PostgreSQL as the system of record. Modules own logical data and access it through scoped repository ports. Use SQLAlchemy async; introduce migrations only in a later phase.

## Alternatives considered

SQLite simplifies a single-host pilot but complicates concurrent workers and planned scaling. A document store can hold event payloads but weakens multi-entity transactional invariants without additional design.

## Consequences

Backups, restore tests, retention cleanup, indexes and transaction boundaries are operational obligations. Redis is not a substitute for durable audit or outbox state.

## Security implications

Parameterization, tenant predicates, least-privilege roles, encryption of provider credentials and backup protection are required. Append-only intent is an application/database permission model, not cryptographic immutability.

## Requirement references

FR-007–019, FR-034–038, FR-047–053; NFR-003, NFR-006; SEC-004, SEC-008, SEC-012, SEC-023; US-002–006, US-015–019, US-025–027.
