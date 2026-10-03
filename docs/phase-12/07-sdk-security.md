# SDK security review

The Phase 12 review checked the following boundaries:

- Credentials: headers only; header-newline rejection; no query parameters, errors, logs,
  `repr`/`toString`, examples, fixtures, or package archives.
- Browser exposure: documentation and examples mark application keys as server-side secrets.
- Network: only configured Renzai `base_url`; HTTP(S) absolute URL required; redirects disabled;
  TLS verification remains enabled; no telemetry or provider calls.
- Logging: off by default; optional records contain method, route template, status, request ID, and
  duration only. Content, evidence, cookies, CSRF tokens, and authorization are excluded.
- Responses: streamed into bounded buffers, JSON shape and bounded enums validated, malformed
  payloads rejected, and unknown additive fields ignored.
- Requests: exact allowlists and bounds; Gateway cannot pass arbitrary fields or enable streaming,
  tools/functions, or multimodal content.
- Duplication: mutating/unsafe requests are not retried; idempotency remains caller-controlled.
- Pagination: page size respects 1–100, total pages are bounded, and repeated cursors fail safely.
- Paths: organization/incident/request IDs are encoded before insertion into URL paths.
- Supply chain: Python adds only `httpx`; TypeScript adds no production dependency.

SDK proxy behavior follows the normal `httpx`/runtime environment. This is distinct from the
server's SSRF-protected outbound provider networking.
