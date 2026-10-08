# Bruno API collection

Open this directory in Bruno and select the `Local` environment. The collection uses its cookie jar
for the opaque session. After registration, copy `csrf_token` from the session response into the
environment. Copy returned IDs and the one-time application key into the corresponding local
variables; do not commit populated environment values.

Control-plane writes require the session cookie, exact same-origin `Origin`, and `X-Renzai-CSRF`.
Analyze and Gateway use `Authorization: Bearer <application-key>` and do not use browser-session
credentials. The collection contains only implemented routes for identity bootstrap, organization,
application/environment/key creation, policies, Analyze, Gateway, incidents, analytics, and optional
AI intelligence. Gateway succeeds only after a real provider is configured; AI intelligence remains
optional and advisory.
