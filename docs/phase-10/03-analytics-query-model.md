# Analytics query model

`AnalyticsService` owns all aggregate queries. The route validates typed query parameters and delegates; it contains no aggregation SQL. Queries use `COUNT`, `COUNT DISTINCT`, `CASE`, `GROUP BY`, and PostgreSQL `date_trunc`, and every query includes `organization_id`. Application/environment IDs are checked against the selected tenant and parent chain before aggregation; a foreign ID is indistinguishable from a missing ID.

The service reads `security_events`, `analysis_results`, `findings`, `gateway_provider_calls`, `provider_configurations`, `incidents`, `applications`, and `environments`. It does not load raw event content, finding evidence, provider credentials, incident summaries, or comments. It creates no audit event because dashboard reads do not mutate organization state.

Direct aggregates are the V1 strategy. There is no analytics cache or materialized view, so correctness has no invalidation dependency. Four additive composite indexes support the common tenant/time and provider grouping predicates.
