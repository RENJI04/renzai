# Incident testing and security

Backend tests cover the four Gateway block/review paths, provider-call counts and output withholding, durable analysis/incident references, sequential deduplication, quiet allow and Analyze behavior, list filters, signed cursors, detail, every lifecycle edge, version conflicts, assignment rules, all five roles, comments/XSS treatment, false-positive immutability, privacy states, retention survival, and tenant hiding.

The opt-in PostgreSQL suite proves the automatic unique-key race and conflicting status transitions using independent sessions. Migration verification uses upgrade, metadata drift, downgrade to `20260928_0004`, and re-upgrade on live PostgreSQL. The Phase 9 benchmark measures indexed list and detail queries with 100 and 1,000 deterministic rows; it is a local comparison, not an SLA.

The security review focuses on IDOR, role escalation, foreign assignment, stored XSS, raw-content and metadata leakage, false-positive side effects, duplication races, retention cascade direction, bounded pagination, and safe Gateway failure. No incident value is logged by new code, and no runtime path writes a detector corpus or source file.
