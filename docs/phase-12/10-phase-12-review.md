# Phase 12 review

Phase 12 adds focused V1 integration clients without changing frozen server semantics or database
schema. Python provides sync/async application and explicit session clients. TypeScript provides a
strict, server-oriented fetch client and explicit session client. Both support Analyze, the actual
limited Gateway, stable errors/request IDs, bounded timeouts/retries/responses, caller-controlled AI
idempotency, and safe incident pagination.

Security decisions remain server-side. No detector, risk, policy, authorization, or redaction logic
is reproduced in either package. Gateway requests are request-allowlisted and cannot opt into
streaming, tools/functions, multimodal content, or arbitrary passthrough. Package documentation
warns against browser API-key exposure and explains the backend proxy pattern.

Tier 3 administrative APIs were intentionally excluded. There is no package publication and no
new migration. The repository lacks a project license file; package metadata therefore does not
invent one, and external publication remains a known blocker. Phase 13 work is not included.
