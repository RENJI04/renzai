# Incident data model

Migration `20261001_0005` adds `incidents`, `incident_security_events`, `incident_comments`, and `incident_timeline_events`. IDs are UUIDv7. `Incident` snapshots organization/application/environment, triggering event and analysis IDs, trigger rule, status, severity, score, category/detector, action, source/direction, safe title/summary, assignee, resolution metadata, privacy/retention settings, timestamps, and an optimistic-concurrency version.

Automatic identity is database-unique on `(organization_id, primary_event_id, trigger_rule_id)`, matching Phase 3. Manual idempotency uses `(organization_id, manual_idempotency_key)`. Composite foreign keys enforce incident-to-application/environment ancestry, assignee membership, incident relation tenancy, and analysis/event pairing. Status, severity, action, source, relation uniqueness, comment length, timeline type, and version have database checks.

The relation row cascades when retained security evidence expires; the incident itself has no cascading event/analysis foreign key and therefore survives. Detail then reports `content_no_longer_retained`. Application/environment archival is a state change, not deletion, so historical incidents remain readable. Membership rows are retained and deactivated rather than erased; only an active same-organization incident editor is eligible for new assignment.
