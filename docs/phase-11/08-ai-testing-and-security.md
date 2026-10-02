# AI testing and security

Tests cover all four task schemas, malformed policy drafts, encrypted credentials, HTTP-header control-character rejection, SSRF inheritance, prompt/data separation, secret/PII scrubbing, no-provider operation, duplicate request and worker delivery, provider failure isolation, queued disclosure revocation, tenant foreign keys, hidden cross-tenant reads, all five roles, privacy modes, provenance, and browser-storage absence.

Security review conclusions:

- Prompt injection remains inside a JSON `untrusted_incident_data` field beneath a fixed system instruction; no tools are available.
- Credentials are purpose-separated and masked; raw requests/responses are not logged or stored.
- AI JSON is untrusted and strictly validated; React escapes displayed text.
- AI cannot write enforcement state or activate policy.
- Output, response size, task type, context, attempts, and in-flight duplication are bounded.
- Worker messages carry IDs only and re-fetch tenant-scoped records.
