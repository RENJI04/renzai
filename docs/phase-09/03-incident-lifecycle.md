# Incident lifecycle

Every incident starts `open`. Domain code owns the exact transitions:

- `open` → `investigating`, `resolved`, `ignored`, or `false_positive`
- `investigating` → `open`, `resolved`, `ignored`, or `false_positive`
- `resolved`, `ignored`, or `false_positive` → `investigating` only with a bounded reason

Terminal transitions set `resolved_at`, resolution category, and optional reason. Reopening clears terminal metadata except for the documented reopen reason. A version integer plus a PostgreSQL row lock prevents lost status and assignment updates; stale versions return `conflict`. Invalid graph edges or missing reopen reasons return `invalid_transition`.

False-positive classification appends timeline and audit facts only. It never edits findings, risk contributions, risk-profile versions, policy decisions, detector files, policies, or a source corpus.
