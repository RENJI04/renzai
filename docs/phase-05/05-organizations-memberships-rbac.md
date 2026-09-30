# Organizations, memberships, and RBAC

Organization creators become Owners. Organization configuration currently exposes the Phase 3 organization-level audit-retention override, bounded to 90–3650 days, with the configured 365-day default. Membership roles are Owner, Admin, Security Analyst, Developer, and Viewer.

Tenant context is derived from the authenticated user and an active membership, never trusted from the URL alone. Foreign and absent tenant resources share `not_found_or_hidden`. Organization administration serializes on a PostgreSQL advisory transaction lock and re-reads the actor and target membership with row locks. This closes concurrent stale-authorization races as well as protecting the final Owner. Details are in [tenancy and concurrency](04-tenancy-rbac-and-concurrency.md).
