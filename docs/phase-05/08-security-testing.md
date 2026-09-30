# Security testing

Automated coverage includes email normalization and uniqueness, generic failed login, opaque-verifier behavior, missing CSRF, hostile origin, logout revocation, reset replay and global revocation, verification replay, disabled account, idle expiry, invitation acceptance, non-admin denial, uniform cross-tenant 404, role-change session invalidation, last-owner conflict, tenant audit creation, and rate limiting.

Backend request tests use isolated SQLite only for speed. The migration is independently round-tripped. Live PostgreSQL 17 verified migration transactions and the competing-owner advisory-lock path; live Redis 7 verified connectivity and fixed-window increments. Frontend checks cover unauthenticated bootstrap, registration, logout cache clearing, organization switching, role-aware controls, the shared API client, strict types, lint, and production build.
