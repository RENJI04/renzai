# Non-functional requirements register

- **NFR-001** Local deterministic simple-text analysis SHOULD target completion below 100 ms in a documented benchmark environment; this is a target, not an unconditional SLA.
- **NFR-002** Core analysis and policy enforcement MUST remain usable when an external AI provider is unavailable.
- **NFR-003** APIs SHOULD be stateless where practical so instances can scale horizontally.
- **NFR-004** The design MAY introduce Redis later for cache, rate-limit, and queue workloads without making it a Phase 1 implementation artifact.
- **NFR-005** Passwords MUST use an Argon2-class password-hashing scheme.
- **NFR-006** Application API keys MUST not be retained in plaintext after creation, and provider credentials MUST be encrypted at rest.
- **NFR-007** Authorization, input validation, and rate limiting MUST be enforced server-side.
- **NFR-008** Normal application logs SHOULD avoid raw sensitive content and use structured redaction.
- **NFR-009** Future implementation MUST organize code as clearly separated modules within a modular monolith.
- **NFR-010** The security engine MUST be independently testable; the test strategy MUST include unit, integration, API, frontend, end-to-end, and security-regression levels as applicable.
- **NFR-011** The design MUST support structured logs, request/correlation IDs, and metrics- and tracing-ready instrumentation.
- **NFR-012** Deployment documentation MUST target Docker-first, Linux-primary self-hosting and modern-browser frontend use; Phase 1 does not implement deployment.
- **NFR-013** Documentation MUST include future developer setup, API, architecture, and security documentation; Phase 1 supplies the product baseline only.
- **NFR-014** Public error behavior MUST be stable enough for clients to distinguish validation, authentication, authorization, rate-limit, provider, and internal failures without disclosing secrets.
- **NFR-015** Request processing MUST define bounded input sizes and provider timeouts before implementation.
- **NFR-016** Product terminology, requirement IDs, and traceability references MUST remain unique and version-controlled.
