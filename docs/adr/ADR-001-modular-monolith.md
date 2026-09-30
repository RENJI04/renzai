# ADR-001: Modular monolith for V1

**Status:** Accepted for Phase 2 architecture

## Context

V1 needs coupled tenant, security, risk, policy and incident behavior while remaining self-hostable and testable. Phase 1 explicitly favors a modular monolith (NFR-009).

## Decision

Use one FastAPI backend application with internal domain modules and public interfaces. A Celery worker may run the same application use cases asynchronously; modules are not separate network services. Measure load and boundaries before any V2+ extraction.

## Alternatives considered

Microservices offer independent deployments but add distributed consistency, network latency and operational burden. A single unstructured application is simpler initially but obscures ownership and increases coupling.

## Consequences

One repository and transaction boundary simplify V1 changes and testing. Independent scaling of a single domain is limited until extracted; API and worker replicas can still scale separately. Extraction requires evidence on load, isolation, ownership and deployment cost.

## Security implications

Tenant and authorization checks remain one backend responsibility. Module boundaries prevent accidental direct data access, but code review/tests must enforce them.

## Requirement references

NFR-003, NFR-009–010; FR-012, FR-020–046; SEC-004; US-007–025.
