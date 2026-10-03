# Tenant, RBAC, and database hardening

The audit traced organization qualification through memberships, applications, environments, keys,
policies, providers, incidents/evidence, analytics, and AI configuration/request/result services.
Existing tenant-composite foreign keys and unique/partial indexes cover the cross-tenant relationship
boundaries; no missing constraint justified a Phase 13 migration. Hidden-resource behavior remains
the authoritative response to cross-tenant identifiers.

## Test-driven RBAC matrix

`test_phase13_rbac_matrix.py` exercises these backend permissions for all roles. A check mark means
allowed; a dash means denied by the backend (frontend visibility is not authority).

| Capability | Owner | Admin | Security analyst | Developer | Viewer |
| --- | :---: | :---: | :---: | :---: | :---: |
| Organization/member administration | ✓ | ✓ | — | — | — |
| Application/environment/key administration | ✓ | ✓ | — | ✓ | — |
| Policy administration | ✓ | ✓ | ✓ | — | — |
| Provider administration | ✓ | ✓ | — | — | — |
| Incident mutate / read | ✓ | ✓ | ✓ | — / ✓ | — / ✓ |
| Playground Analyze | ✓ | ✓ | ✓ | ✓ | — |
| Analytics read | ✓ | ✓ | ✓ | ✓ | ✓ |
| AI configuration administration | ✓ | ✓ | — | — | — |
| AI request/read | ✓ | ✓ | ✓ | — | — |

Last-owner demotion/removal, policy priority, automatic incident deduplication, incident optimistic
versioning, AI one-in-flight request, worker claim, idempotent result, and tenant-composite
configuration/result relationships remain enforced by database locks/constraints and covered by the
existing PostgreSQL integration suite. SQLite tests are not represented as proof of PostgreSQL row
locking. Live execution status is recorded in the Phase 13 review.

Retention relationships preserve incidents when retained analysis/security-event evidence is
deleted; only the relation is removed. Audit history remains append-style. No Phase 13 change
weakened cascade direction, privacy-mode non-retention, or tenant-qualified analytics.
