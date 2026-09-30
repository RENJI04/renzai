# Provider errors and failure modes

Stable Gateway errors use the Renzai envelope: invalid requests are 422 `validation`; bad application keys are 401 `authentication`; limits are 429 `rate_limit`; policy blocks are 403 `policy_block`; review decisions are 409 `review_required`; provider timeouts are 504 `provider_timeout`; other network, protocol, size, redirect, and malformed response failures are 502 `provider_error`; inspection failures are 503 `inspection_failure`; unusable configuration is 503 `configuration_error`.

Raw provider bodies and headers are not exposed. Errors contain no provider content, credential, base URL, authorization header, Renzai application key, cookie, or detector evidence. Provider-call persistence records only tenant/provider IDs, configured model, correlation ID, latency, safe status class when known, outcome, and related analysis IDs.

Chat completions are attempted exactly once. Timeouts, connection resets, and upstream 5xx responses are not automatically retried because the provider may have processed an uncertain request and a retry could duplicate billing or side effects. V1 health validation also performs one bounded attempt.
