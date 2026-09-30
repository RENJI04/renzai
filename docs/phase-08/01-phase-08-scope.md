# Phase 8 scope

Phase 8 implements the V1 provider layer and a deliberately limited, non-streaming OpenAI-style chat Gateway. It adds encrypted environment-scoped provider configuration, a framework-independent provider port, a pinned-destination HTTP adapter, strict request validation, input and output enforcement, safe provider error normalization, persistence, rate limiting, management UI, and verification.

The implemented compatibility boundary is only `POST /v1/chat/completions` with textual `system`, `user`, and `assistant` messages. Streaming, tools/functions, multimodal input, `response_format`, agent execution, automatic completion retries, and generic OpenAI protocol parity are not implemented.

Incidents, notifications, webhooks, AI intelligence, analytics, SDKs, and reviewer workflow remain Phase 9+ work. Existing Analyze behavior remains provider-independent.
