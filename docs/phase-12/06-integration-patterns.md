# Integration patterns

## Analyze before a direct model call

Application-selected user input → Renzai Analyze → application branches on the server action →
application may call its model.

- `allow`: continue.
- `flag`: continue only under the application's documented workflow while retaining the Renzai
  action/request ID.
- `block`: do not call the model.
- `redact`: use only Renzai's returned `redacted_content`; do not invent local redaction logic.
- `require_review`: withhold and enter the application's review workflow.

The application does not recalculate risk or policy. The action came from Renzai.

## Renzai Gateway

Application → Renzai Gateway → configured upstream model. Gateway already performs server-side
input and output inspection and enforcement. Do not duplicate Renzai's risk/policy logic locally.
The V1 Gateway is non-streaming and text-only.

## Incidents, analytics, and AI intelligence

These are operator/control-plane operations authenticated by an existing Renzai user session and
CSRF token, not an application key. Incident mutations expose `version`, and a 409 remains a visible
typed conflict. AI tasks are restricted to the four implemented task types and remain labelled
advisory output; the SDK never converts them into deterministic findings.

Framework examples under `examples/phase-12/` inspect only explicitly selected text. They do not
create middleware that silently copies every request body to Renzai.
