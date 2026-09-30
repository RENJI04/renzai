# Error, logging and request context

Every registered Renzai error returns `error.code`, `error.message`, `error.request_id` and optional allowlisted details. Validation handler details contain field names only. Unexpected exceptions map to generic `internal_error`; no stack trace is sent to the client.

Logging includes UTC timestamp, level and request ID. It redacts values for names containing credentials, tokens, bodies, prompt/response content, sessions and secrets. Raw request body capture is absent. Baseline response headers include `nosniff`, no-referrer, DENY framing and a restrictive permissions policy; HSTS is production-only because it assumes TLS.
