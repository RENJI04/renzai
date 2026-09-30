# Verification and traceability

| Requirement | Implementation | Evidence |
|---|---|---|
| Password identity | user domain, Argon2 adapter, auth service | normalization, duplicate, generic-login tests |
| Opaque sessions | auth models/service/dependencies | verifier, logout, expiry, disabled-account tests |
| CSRF and origin | API dependencies | missing-CSRF and hostile-origin tests |
| Reset/verification | auth service/routes | replay and session-revocation tests |
| Organizations | organization service/routes | create/list/get tests in end-to-end flow |
| Invitations and RBAC | membership domain/service | acceptance and denial tests |
| Tenant isolation | tenant dependency | cross-tenant uniform 404 test |
| Privilege freshness | user/session privilege version | role-change invalidation test |
| Last owner | advisory lock + owner row locks | invariant test; PostgreSQL concurrency verification when available |
| Auditing | audit and account-security models | tenant audit query test |
| Schema | Alembic revision | upgrade/downgrade verification |
| Frontend | identity console and API client | Vitest, lint, typecheck, production build |

SQLite is used for deterministic request tests, not as evidence for PostgreSQL locking semantics. Live PostgreSQL/Redis results are recorded in the Phase 5 review only when actually executed.
