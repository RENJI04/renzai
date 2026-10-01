# Incident API

All routes use the stable Renzai error envelope, opaque session authentication, tenant membership, and CSRF on writes.

- `GET /api/v1/organizations/{org}/incidents` lists newest first. Filters: repeated `status`/`severity`, `application_id`, `environment_id`, `assignee_user_id`, `unassigned`, `source`, `action`, `category`, `from`, `to`, and safe `search`. Signed filter-bound cursors prevent cross-query reuse. Default limit is 50; maximum 100.
- `GET /api/v1/organizations/{org}/incidents/{incident}` returns metadata, related analysis references, privacy-aware analysis/findings/risk/policy, timeline, and comments.
- `POST /api/v1/organizations/{org}/incidents` creates a manual incident and supports a bounded `Idempotency-Key`.
- `PATCH /api/v1/organizations/{org}/incidents/{incident}/status` accepts status, optional reason, and version.
- `PATCH /api/v1/organizations/{org}/incidents/{incident}/assignment` accepts assignee or null plus version.
- `POST /api/v1/organizations/{org}/incidents/{incident}/comments` adds bounded plain text.
- `GET /api/v1/organizations/{org}/incidents/assignees` returns eligible active members to incident editors.

Search covers incident UUID, safe title, and safe summary only. Arbitrary sorting and raw-content search are not supported.
