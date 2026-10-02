# AI context and privacy

Context version `1.0.0` uses bounded structured fields: incident state, deterministic finding metadata, risk snapshot, and policy-decision metadata. Operator comments are excluded. Expired source evidence is represented as an explicit state and does not prevent metadata-only assistance.

`metadata_only` excludes textual explanations and content. `redacted` includes only scrubbed safe explanations. `full` requires all three conditions: source incident privacy was `FULL`, the AI configuration explicitly permits full external disclosure, and the requester is Owner/Admin. Storage mode alone never authorizes external disclosure.

Because processing is asynchronous, the worker re-checks the current incident privacy mode and current provider full-content consent immediately before provider generation. Revocation fails the request with `disclosure_revoked`, persists no AI result, and makes no provider call.

Before outbound use, textual values are scrubbed for API-key patterns, secret assignments, email addresses, and phone numbers. Raw prompts and constructed provider requests are not persisted.
