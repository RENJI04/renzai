# Limited OpenAI-compatible provider

The `ChatProvider` port accepts a bounded `ProviderChatRequest` and runtime configuration and returns a normalized `ProviderCompletion`. Security detectors, risk, and policy modules do not import the HTTP adapter and do not know provider semantics.

The implemented adapter posts JSON to the safely normalized `<base>/v1/chat/completions` endpoint, or the equivalent when the configured base already ends in `/v1`. Remote credentials are decrypted immediately before use and sent only as the provider `Authorization: Bearer` value. Local providers may omit credentials. The Renzai application key, cookies, CSRF value, tenant IDs, policy data, and arbitrary caller fields are never forwarded.

Responses must be bounded JSON with exactly one textual assistant choice, the configured model, and `finish_reason` of `stop` or `length`. Only safe numeric usage counters are retained. Raw upstream headers, error bodies, and malformed structures are normalized to `provider_error`; timeouts become `provider_timeout`.

Health validation performs a bounded `GET /v1/models` through the same target guard and health timeout. It sends no user content. This is a point-in-time validation, not permanent network authorization.
