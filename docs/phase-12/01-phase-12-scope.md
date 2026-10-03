# Phase 12 scope

Phase 12 delivers local, publishable Python and TypeScript packages that are thin clients over the
implemented Renzai API v1. The server remains authoritative for detection, risk, policy,
authorization, tenancy, incidents, analytics, and optional AI intelligence.

## Included

- Application-key clients for synchronous Analyze and the limited Gateway.
- Python sync and async clients; TypeScript standards-based `fetch` client.
- Runtime validation of critical response envelopes, typed errors, request IDs, timeouts, bounded
  response reads, conservative retries, safe logging, and cursor pagination safeguards.
- Explicit session-plus-CSRF clients for implemented incident, analytics, and AI intelligence
  routes. These routes are not falsely exposed as application-key operations.
- Local package builds, unit/contract fixtures, local-server compatibility tests, examples, and
  integration/security guidance.

## Deliberately omitted

- Streaming, tools/functions, multimodal content, arbitrary Gateway passthrough, and claims of
  full OpenAI compatibility.
- Provider, policy, application, environment, and key administrative clients. These lower-priority
  control-plane APIs would materially enlarge the V1 surface and are not required for integration
  runtime use.
- Notifications, webhooks, SIEM/Slack/email/GitHub integrations, IDE plugins, MCP, autonomous
  agents, billing, telemetry, and API v2.

No database migration or backend feature change is part of Phase 12. Phase 11 remains the frozen
server baseline.
