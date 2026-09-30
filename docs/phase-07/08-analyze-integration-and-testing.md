# Analyze integration and testing

The canonical response now includes score, final severity, strongest-finding confidence, profile/version, safe contributions, selected action, evaluated policy versions, scope winners, rationale, and timing. `safe`/`no_detected_threat` remain observational: a valid pass with zero findings and score zero. Policy allow never erases findings.

`redact` uses Phase 6 validated typed spans and returns `redacted_content`; it does not overwrite original FULL-mode storage. If no requested target can be safely applied, Analyze returns HTTP 503 with `inspection_failure` and never returns original content as successfully redacted.

Tests cover exact vectors and integer boundaries, overlap/corroboration, critical floor, grammar, precedence, CRUD/version activation/rollback, priority conflicts, RBAC/tenancy, baseline idempotency, all actions, redaction failure, persistence, migration round trips, and frontend behavior.

On the Phase 7 Windows/Python 3.14 verification host, the repeatable `scripts/benchmark_phase7.py` microbenchmark measured approximately 5.7/19.6/41.8 µs per risk evaluation for 0/1/3 findings and 30.2/186.5 µs for worst-case traversal of 10/100 policies. These measurements describe that host and are not a universal SLA.
