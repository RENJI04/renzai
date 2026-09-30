# Stable Renzai error contract

Every failed API or Gateway request returns an HTTP status plus this JSON envelope. Renzai-owned fields use `snake_case`; `request_id` is a safe correlation identifier created/validated at the edge.

```json
{
  "error": {
    "code": "validation",
    "message": "The request is invalid.",
    "request_id": "<correlation-id>",
    "details": { "fields": ["messages"] }
  }
}
```

`details` is optional and contains only allowlisted field names or safe enum values; it never echoes submitted content, credentials, provider responses, internal URLs, stack traces or cross-tenant identifiers. Unknown/internal failures use a generic message. Codes are stable within `/api/v1` and the limited Gateway contract; messages may be localized/reworded without changing code. HTTP mappings are proposed V1 contracts:

| Code | HTTP | Meaning / disclosure rule |
|---|---:|---|
| `validation` | 422 | Bounded parse/field error; no value echo. |
| `authentication` | 401 | Missing/invalid/expired session or application key; uniform safe response. |
| `authorization` | 403 | Known tenant member lacks action permission. |
| `not_found_or_hidden` | 404 | Missing or inaccessible tenant resource; indistinguishable cases. |
| `conflict` | 409 | Uniqueness/state invariant, e.g. duplicate policy priority or last Owner. |
| `rate_limit` | 429 | Limit exceeded; safe `Retry-After` where useful. |
| `policy_block` | 403 | Deterministic policy block; not a generic auth denial. |
| `review_required` | 409 | Gateway input/output withheld for review; safe `phase=input|output` detail. Analyze returns successful result action instead. |
| `provider_timeout` | 504 | Upstream did not complete before bound. |
| `provider_error` | 502 | Upstream failed or produced invalid bounded response. |
| `inspection_failure` | 503 | Security decision invalid/unavailable; staging/production Gateway fails closed. |
| `configuration_error` | 503 | Required configuration invalid/missing; internal details hidden. |
| `internal_error` | 500 | Unexpected failure; log safe correlation ID only. |

`not_found_or_hidden` applies even when a foreign UUID is well formed; returning `authorization` for one foreign object and 404 for a nonexistent object would leak existence. `policy_block` and `review_required` may share an HTTP class with other errors but have distinct machine codes and messages. Gateway never exposes raw provider error body. A successful no-policy-match decision is not an error and returns `allow` with `no_policy_matched` rationale. The body of `/ready` is deliberately minimal and uses 503 without internal dependency names when unavailable.
