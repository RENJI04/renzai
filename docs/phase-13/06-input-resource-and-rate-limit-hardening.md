# Input, resource, and rate-limit hardening

A pre-parser ASGI limit now covers every mutating request. The default JSON body ceiling is 256 KiB
(hard configuration ceiling 1 MiB); Analyze/Playground uses the lower 64 KiB route ceiling and the
Gateway uses its existing lower 96 KiB ceiling. Duplicate, invalid, negative, or excessive
Content-Length values and streamed bodies that cross the effective limit receive the stable body
validation error before model/auth work continues.

Analyze remains limited to 32 KiB of UTF-8 content. Metadata is at most 16 entries, with 1–64
character keys and values no longer than 256 characters. Security-sensitive models forbid unknown
fields. Existing limits remain for Gateway message count/combined bytes/options, incident text,
policy conditions/operators/facts, provider configuration, and AI schemas/output.

Normalization stays single-pass and bounded by input bytes, eight candidates, 4,096 candidate
characters, four-times expansion, and no recursive transform feeding. The detector and scrubber
regex review found no new catastrophic-backtracking path. The Phase 13 benchmark exercises a 32 KiB
plain input, a 32 KiB candidate-heavy encoded input, and a 32-message Gateway inspection payload.

| Boundary | Key material | Default / failure behavior |
| --- | --- | --- |
| Login/registration | Keyed digest of operation, normalized identity, source | 5 / 900 seconds; Redis failure denies |
| Password reset/confirm | Keyed digest of operation, identity/lookup, source | 3 / 3,600 seconds; Redis failure denies |
| Cookie-authenticated mutations | Keyed digest of user and session IDs | 120 / 60 seconds; Redis failure denies |
| Analyze | Keyed application-key identifier | 60 / configured window; Redis failure denies |
| Gateway | Keyed application-key identifier | 30 / 60 seconds; Redis failure denies |
| AI request/provider validation | Session boundary plus workflow/idempotency bounds | Session limiter and server constraints |

Raw passwords, tokens, session values, API keys, and caller strings are not Redis key components.
