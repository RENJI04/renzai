# E2E and concurrency testing

The `e2e` selector collects 14 representative cases rather than duplicating every unit scenario.
It covers identity/session lifecycle, password reset/change revocation, application/environment/key
lifecycle, deterministic Analyze replay, full Gateway inspection/provider/output persistence,
incident lifecycle and role matrix, dashboard aggregation, and all four AI tasks.

Two-tenant isolation is exercised at HTTP and service/database boundaries for applications,
playground, policies, providers, incidents, analytics, and AI. Representative Owner, Admin,
Security Analyst, Developer, and Viewer HTTP behavior is covered by incident and AI role matrices;
the Phase 13 constant matrix remains a separate consistency check.

The `concurrency` selector collects five PostgreSQL cases:

1. one active Owner after competing owner mutations;
2. one policy at a tenant/scope/phase/priority after competing inserts;
3. one automatic incident and one winning optimistic transition;
4. one in-flight AI request after concurrent attempts;
5. one AI provider-execution owner and one result after duplicate worker delivery.

Concurrency tests assert outcomes and durable rows rather than timing. A small provider delay widens
the worker overlap but correctness depends on the atomic pending-to-running update and unique
constraint, not on the delay.

The deterministic local provider doubles cover success, 500/error, timeout/slow response, malformed
and deeply nested JSON, oversized body/headers, redirects, duplicate framing, secret-bearing and
hostile content. No paid provider is contacted.
