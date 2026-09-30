# Persistence and migration

Alembic revision `20260924_0001` creates:

- `users` and `password_credentials`
- `sessions`, `password_reset_tokens`, and `email_verification_tokens`
- `organizations`, `memberships`, and `invitations`
- `audit_events` for tenant-scoped durable audit history
- `account_security_events` for global registration/login/password/verification activity

UUID columns contain application-generated UUIDv7 values. Foreign keys define ownership and cascade only for records whose lifecycle is subordinate. Unique constraints cover normalized email, organization slug, token/session lookup, user credential, and organization/user membership. Expiry, tenant, identity, status, role, action, and timestamp indexes support the Phase 5 access paths.

`audit_events.organization_id` remains non-null to preserve the Phase 3 tenant-audit contract. Global identity events are not silently mixed into it; the bounded `account_security_events` record is deliberately separate. Both metadata fields are safe JSON and exclude raw credentials.

Apply with `python -m alembic upgrade head`. The app does not create or mutate schema at startup.
