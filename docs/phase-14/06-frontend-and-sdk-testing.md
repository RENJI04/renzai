# Frontend and SDK testing

Frontend component tests cover the unauthenticated identity flow, registration and session
bootstrap, logout, tenant switching, owner/viewer visibility, dashboard calculations and empty/error
states, Security Playground analysis, one-time keys, provider credential handling, incident queue,
AI intelligence, and security headers. Phase 14 adds provider loading/error/empty-state coverage and
checks critical form labels plus live-region semantics for workspace loading and password-reset
feedback.

The accessibility review is pragmatic, not a WCAG certification. Critical inputs have programmatic
names, mutation errors use alerts, loading/notice states are announced, native buttons/forms/details
retain keyboard behavior, and tables/components retain semantic markup. Backend authorization tests
remain authoritative for RBAC.

`verify_phase14_frontend_backend.py` starts the real FastAPI app and Next development server on free
loopback ports. It verifies the rendered shell, Next `/api` rewrite, session cookie propagation,
CSRF-authenticated write, and organization read using synthetic data. It does not require a browser
download or external network.

The Python SDK suite covers `Renzai`, `AsyncRenzai`, `RenzaiSession`, Analyze, Gateway, errors,
timeouts, cancellation, session/CSRF headers, pagination, AI requests, request IDs, secret-safe repr,
malformed data, and response bounds. The TypeScript suite covers the equivalent surface including
`AbortSignal`, header/base-URL validation, and non-streaming Gateway restrictions.

`verify_phase12_compatibility.py` now compares semantically equivalent Analyze fields from both SDKs
against the same ephemeral local server in addition to Gateway failure and incident reads. Unique
IDs and language-specific object representations are intentionally excluded from equality.

Vitest V8 and pytest-cov coverage commands emit text plus JSON/XML summaries where supported.
Frontend coverage is interpreted by tested components and states, not used as a substitute for
backend authorization or browser certification.
