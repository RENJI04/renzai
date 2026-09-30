# Tenancy, RBAC, and concurrency

An organization is the tenant boundary. Every organization lookup first resolves an active membership for the authenticated user. Foreign or nonexistent tenant resources return the same `not_found_or_hidden` 404 response.

Roles are `owner`, `admin`, `security_analyst`, `developer`, and `viewer`. Owners may assign every role and manage owners. Admins may manage only non-owner memberships and cannot grant ownership. Other roles cannot administer membership. Authorization reads current membership state on each request; sessions do not cache tenant roles.

Role changes and removals increment the affected user's global privilege version. Existing sessions then fail their next freshness check. New invitation acceptance does not invalidate the accepting browser because membership authorization is already read live.

Owner demotion/removal on PostgreSQL takes a transaction-scoped advisory lock derived from the organization UUID, then locks active owner membership rows before counting them. The mutation conflicts if it would remove the last owner. This serializes concurrent owner transitions within one organization while allowing different organizations to proceed independently.
