# Time bucketing and filters

Windows are fixed enums: `24h`, `7d`, `30d`, and `90d`; default is `24h`. The 24-hour response contains exactly 24 hourly UTC buckets. Longer windows contain exactly 7, 30, or 90 daily UTC buckets. The current hour/day is partial. Bounds are inclusive (`occurred_at >= window_start` and `<= window_end`), and missing buckets are returned with zero counts.

Each activity bucket contains `bucket_start`, analysis count, threat count, blocked count, and review count. PostgreSQL performs native UTC `date_trunc`; the SQLite-only unit path uses equivalent `strftime` semantics.

Global filters are `application_id`, `environment_id`, and the bounded `source` enum (`analyze`, `playground`, `gateway`). Environment requires application. Changing the application in the UI clears environment. Source consistently filters analyses and incidents; provider data and Gateway request totals appear only for all sources or Gateway. Query keys include organization, window, application, environment, and source.
