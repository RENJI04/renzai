# ADR-014: Shared SSRF-controlled outbound networking

**Status:** Accepted for Phase 2 architecture

## Context

Configured provider URLs and webhook destinations are untrusted. Phase 1 OQ-006 and SEC-020 require HTTPS defaults, denied private/metadata targets and validation across DNS and redirects.

## Decision

Route provider and webhook HTTP through one guard. Reject credential-bearing URLs, unsafe schemes and denied IPv4/IPv6 ranges by default. Revalidate all resolved IPs at connection time and every redirect, bind connection to approved resolution, and constrain proxy behavior. Local/private provider access requires explicit self-hosted destination-specific opt-in.

## Alternatives considered

Validation only when saving a URL fails under DNS rebinding or later redirects. A broad private-network allowlist is easy to operate but exposes internal services. Network egress controls alone cannot express tenant/config-specific exceptions.

## Consequences

Some local-provider deployments need extra configuration. DNS/proxy libraries and egress topology require careful tests; a guard cannot eliminate SSRF risk absolutely.

## Security implications

Webhook destinations do not inherit provider local exceptions. Timeouts, response limits and redirect caps bound abuse; deployment firewall remains defense in depth.

## Requirement references

OQ-006; FR-042, FR-050, FR-056; SEC-020–022; US-021, US-031.
