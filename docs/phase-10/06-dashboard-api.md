# Dashboard API

`GET /api/v1/organizations/{organization_id}/analytics/dashboard`

The endpoint uses the opaque session and current active organization membership. Owner, Admin, Security Analyst, Developer, and Viewer may read it, matching the Phase 1 matrix. Query parameters are:

- `window`: `24h` (default), `7d`, `30d`, or `90d`
- `application_id`: optional tenant-owned application UUID
- `environment_id`: optional UUID, valid only with its application
- `source`: optional `analyze`, `playground`, or `gateway`

The bounded response contains filter/boundary metadata, summary, activity buckets, risk/action distributions, top threat/detector metrics, application/environment breakdowns, provider usage, incident distribution, five recent incidents, and server-side query duration. Invalid enums/shape return validation errors. Foreign scope identifiers return `not_found_or_hidden`. The endpoint does not support custom SQL/group/sort expressions or arbitrary date ranges.
