# Input and output enforcement

Input inspection uses the existing `AnalysisService`. The deterministic representation version is `gateway-messages-v1`: each message becomes `[role]\ncontent`, and messages are joined with two newlines. The wrapper preserves role boundaries without modifying content before detection.

After validation, authentication, and the separate application-key Gateway rate limit, input analysis is durably committed before any provider network call. `allow` and `flag` forward; `redact` forwards only per-message content for which existing detector spans produce the configured typed placeholders. `block` returns 403 `policy_block`, `require_review` returns 409 `review_required`, and inspection or redaction failure returns 503 `inspection_failure`; none contacts the provider.

The database transaction is closed before waiting on provider I/O. Provider output is untrusted and is never sent to the client before a second `AnalysisService` pass is durably recorded. Output `allow`/`flag` returns normalized content, `redact` returns only safely redacted content, `block` withholds content with 403, and `require_review` withholds content with 409. Analysis or redaction failure withholds content with 503.

The external call cannot be atomically rolled back. Persistence therefore records input first, performs the provider call without an open transaction, then records output and safe provider-call metadata. A failure to persist a required input or output decision fails closed.
