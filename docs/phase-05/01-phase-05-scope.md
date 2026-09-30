# Phase 5 scope

Phase 5 implements the V1 human identity and organization boundary on the Phase 4 foundation. It includes users, password credentials, sessions, password reset, optional email verification, organizations, membership, invitations, RBAC, tenant context, audit/security records, HTTP APIs, and a minimal web console.

Explicitly deferred: applications, API keys, detectors, analysis, findings, risk, policy, incidents, providers, gateway forwarding, notifications, webhooks, analytics, billing, SSO, MFA, and SCIM. Phase 6 has not started.

The implementation keeps Phase 3 contracts stable: UUIDv7 IDs, opaque sessions, 30-minute idle and 12-hour absolute limits, same-origin CSRF, generic login failures, uniform tenant 404s, five roles, and organization-scoped audit events.
