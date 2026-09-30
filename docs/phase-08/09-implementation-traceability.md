# Phase 8 implementation traceability

| Authority | Phase 8 evidence |
|---|---|
| FR-041, US-022, NFR-002 | Analyze and deterministic security remain provider-independent; missing provider affects only Gateway forwarding. |
| FR-042, US-021 | Environment-scoped provider model, encrypted secret, masked management API/UI, health validation, remote/local target policy. |
| FR-044, US-008 | Strict limited `POST /v1/chat/completions`, textual roles, generation allowlist, normalized one-choice response. |
| FR-045, US-011/013/014 | Existing analysis/risk/policy runs before forwarding and before output return; block/review withholding and typed redaction are tested. |
| FR-046, US-023 | Inspection fails closed; provider timeout/error are stable and secret-free; no completion retry. |
| FR-047/048, US-025 | Provider changes and validation append safe audit events; Gateway uses security-event persistence rather than per-request audit spam. |
| FR-051/052/053, US-026 | Gateway input/output reuse existing privacy-aware `SecurityEvent` persistence and retention. |
| SEC-004/007/016/017 | Tenant ancestry, RBAC, strict bounds, separate key-scoped rate limits, stable safe errors. |
| SEC-010/012/013/014 | No raw content in normal logs, AES-GCM provider secrets, placeholder configuration, production key separation. |
| SEC-015/020/021 | Provider audit events, pinned validated destinations, HTTPS remote default, exact local opt-in, explicit timeouts and response limits. |
| NFR-006/007/008/009/010/014/015/016 | Encrypted credentials, server enforcement, safe logging, modular boundary, layered tests, stable errors, bounded processing, versioned representation. |

FR-043 AI-generated explanations, FR-049 notifications, FR-050/056 webhooks, incidents, analytics, SDKs, streaming, tools, multimodal requests, and reviewer workflow are explicitly not marked implemented.
