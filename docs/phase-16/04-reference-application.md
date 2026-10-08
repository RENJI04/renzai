# Reference application

[Protected support copilot](../../examples/reference-app/README.md) is a minimal FastAPI app using the
local Python SDK. Browser → reference app → Analyze is server-side. A deterministic local mock
provider means no paid provider or credential is required.

The reference app withholds its provider path on `block` and `require_review`, uses only returned
`redacted_content` for `redact`, and visibly reports action, score, request ID, and whether the
provider ran. It neither reimplements policy nor simulates unsupported streaming, tools, multimodal,
or Gateway behavior. An invalid or absent `redacted_content` on a `redact` decision fails closed
without calling the mock provider or returning the original prompt. Tests prove the safe, blocked,
and redaction-failure paths.
