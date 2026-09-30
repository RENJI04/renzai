# ADR-006: Opaque server-side dashboard sessions

**Status:** Accepted for Phase 2 architecture

## Context

Phase 1 OQ-001 explicitly chose opaque sessions and Secure/HttpOnly cookies for dashboard users; CSRF protection is required.

## Decision

Issue cryptographically random session credentials in Secure, HttpOnly cookies. Store a keyed verifier and server-side expiry/revocation metadata, not the plaintext credential. Rotate on login/privilege elevation; enforce idle and absolute timeouts; validate CSRF on state changes.

## Alternatives considered

Browser JWTs reduce server lookup but complicate immediate revocation and contradict the approved default. Plaintext session storage increases breach impact. SameSite alone does not satisfy CSRF protection.

## Consequences

Shared session state is required across API replicas. Cookie scope and timeout values are fixed with deployment/API contracts in Phase 3.

## Security implications

Session theft remains possible through endpoint compromise. Password reset and logout must revoke sessions; proxy TLS/cookie configuration and brute-force controls require tests.

## Requirement references

OQ-001; FR-001–006; NFR-005, NFR-007; SEC-001, SEC-003, SEC-005, SEC-024; US-001.
