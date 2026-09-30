# Limited V1 gateway API contract

**Route:** `POST /v1/chat/completions`. Auth: environment-scoped Renzai application key in `Authorization: Bearer <key>`. It is a deliberately limited OpenAI-style subset, not full protocol parity. JSON uses `snake_case` for Renzai-owned fields and supported OpenAI-compatible names for the subset.

## Request allowlist

| Field | V1 contract |
|---|---|
| `model` | Required nonempty string; must equal the configured model or a configured safe alias for this environment. Arbitrary model routing is rejected. |
| `messages` | Required array of 1–32 `{role,content}` objects; role only `system|user|assistant`, content nonempty UTF-8 text. No nested/multimodal parts. |
| `stream` | Optional `false` only; `true` rejected. |
| `temperature` | Optional number 0–2. |
| `top_p` | Optional number >0 and ≤1. |
| `max_tokens` | Optional integer 1–4096, also bounded by configured provider ceiling. |
| `stop` | Optional one string or 1–4 bounded strings. |
| `presence_penalty`, `frequency_penalty` | Optional numbers −2 to 2. |
| `seed` | Optional signed 32-bit integer; forwarded only when the configured provider declares support, otherwise rejected. |

`max_completion_tokens` is not in the V1 allowlist; clients must use `max_tokens`. `tools`, `tool_choice`, `functions`, `function_call`, `response_format`, multimodal content, `stream_options`, arbitrary passthrough fields and unknown fields are rejected with `validation`. Textual tool-manipulation *indicators* remain detector input. General body and combined message limits are in [configuration](19-configuration-contracts.md). Invalid field combinations or provider capability mismatches are rejected before provider forwarding.

## Normal response

On allowed input and allowed/redacted output, return HTTP 200 with one non-streaming chat-completion object: `id`, `object="chat.completion"`, Unix `created`, configured `model`, one `choices[0]` containing assistant textual `message.content` and normalized `finish_reason=stop|length`, and optional provider-confirmed `usage`. Renzai analysis IDs and correlation ID are carried in documented response headers, not raw security evidence in the compatibility body. For output `redact`, `message.content` contains typed placeholders; the security event records action and profile/policy versions. Response content is never returned before output analysis and policy evaluation.

## Gateway outcomes

| Condition | HTTP / code | Forward or return behavior |
|---|---|---|
| Normal completion; `allow|flag` | 200 | Forward after input decision; return checked output. |
| Input `redact` | 200 if output allowed | Forward only redacted input; output still inspected. |
| Input `block` | 403 `policy_block` | No provider call. |
| Input `require_review` | 409 `review_required` | No provider call; durable incident/outbox trigger, no synchronous wait. |
| Input inspection failure | 503 `inspection_failure` | Staging/production fail closed; development exception only if explicitly configured and audited. |
| Provider timeout/error | 504 `provider_timeout` / 502 `provider_error` | Stable safe error; never bypass security. |
| Output `block` | 403 `policy_block` | Provider was called; output withheld. |
| Output `require_review` | 409 `review_required` | Provider was called; output withheld; durable incident/outbox trigger. Same code as input with safe phase detail. |
| Output `redact` | 200 | Return typed-placeholder content only after successful redaction. |
| Output inspection failure | 503 `inspection_failure` | Withhold provider output; development exception requires explicit configuration. |
| Unsupported/unknown field or `stream=true` | 422 `validation` | Reject before forwarding. |
| Missing/invalid key; rate limit | 401 `authentication` / 429 `rate_limit` | No provider call. |

No match after **valid** inspection means `allow` with rationale `no_policy_matched`, even with nonzero risk. This is not the inspection-failure path. A policy `require_review` is a review state, not an assertion of confirmed maliciousness. The error envelope is [Renzai’s stable format](17-error-contracts.md), not a claim of OpenAI error parity. No automatic completion retry is performed on uncertain provider outcomes.
