# ADR-005: Redis and Celery for asynchronous work

**Status:** Accepted for Phase 2 architecture

## Context

Optional AI incident analysis, notifications, webhooks, retention and analytics should not block deterministic request decisions.

## Decision

Use Celery workers with Redis as broker and optional short-lived coordination store. Keep durable work intent in a PostgreSQL outbox and make consumers idempotent. Synchronous security decisions never depend on queue delivery.

## Alternatives considered

In-process background tasks are simpler but lose work on process failure. A larger broker may offer stronger delivery features but adds self-hosting complexity. Direct publish after commit risks lost side effects.

## Consequences

Workers need bounded retries, failure visibility, tenant context and separate scaling. Broker outage delays async work; outbox backlog is monitored.

## Security implications

Do not place raw prompts or credentials in job payloads. Workers revalidate tenant scope and outbound destinations before side effects.

## Requirement references

FR-034, FR-043, FR-049–050, FR-053, FR-056; NFR-002–004, NFR-011; SEC-004, SEC-019–023; US-015, US-024, US-026, US-030–031.
