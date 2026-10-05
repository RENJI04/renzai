# Prometheus and metrics

Metrics default off in Settings; the supplied deployment template explicitly enables them for internal Compose scraping. API metrics cover registered route-template request count, status class, and latency. Unmatched requests use a single sentinel route and unsupported methods use a bounded `OTHER` label. Bounded security counters cover analysis actions, Gateway outcomes, and incident creation/deduplication. Worker metrics cover allowlisted task names, completion status, and duration. Readiness is a gauge. PostgreSQL and Redis exporters expose infrastructure health.

Labels are closed enums or route templates. Request IDs, email addresses, user IDs, organization/application identifiers, prompts, API keys, arbitrary tenant strings, and provider content are forbidden labels. The static verifier and regression tests protect this boundary.

Prometheus is not host-published. The API and worker metrics endpoints are reachable only on Compose networks in the production-like topology. If operators expose them, they must add network access control and treat operational metadata as sensitive.
