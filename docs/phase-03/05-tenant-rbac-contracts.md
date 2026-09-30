# Tenant and RBAC contracts

## Context derivation

For dashboard requests, verify the opaque session, fetch current active membership and role for the selected organization, then construct `ActorContext(user_id, organization_id, role, privilege_version, correlation_id)`. For Analyze/Gateway, verify the application key and construct `ApplicationContext(organization_id, application_id, environment_id, key_id, correlation_id)`. URL/body tenant IDs must match this context and the parent chain. Cross-tenant object IDs are hidden with the same `not_found_or_hidden` response as nonexistent IDs; an authorized member lacking a capability gets `authorization`.

The Phase 1 [role matrix](../phase-01/03-personas-and-actors.md) is normative. Owner alone transfers ownership or performs destructive organization operations; last Owner cannot be removed/demoted. Admin manages members but not owners/destructive organization actions. Security Analyst manages policies and incident status but not provider, retention or webhook configuration. Developer manages apps/environments/keys and can view/comment on incidents. Viewer is read-only. Backend authorization is mandatory for every operation and queued job; UI visibility is not authority.

## Scoping and relationships

`Organization` is the tenant root. `Application.organization_id` is direct. `Environment` derives organization through application and carries an enforced same-tenant reference. Keys, events, incidents, policy, provider, notification, audit and outbox records carry or derive organization ID and cannot reference a parent in another tenant. Every repository query includes the derived tenant predicate; object ID alone is never enough. Foreign-key ownership and composite uniqueness are planned as database invariants. Job messages include tenant/object IDs but workers re-fetch and revalidate; Redis cache keys include tenant and permission scope.

## Authorization decisions

Permission checks occur in use cases before private data access and again in owner-specific mutations. Role changes and removals are audited. A Developer’s incident comment can add integration context but cannot change assignee/status. Invitation acceptance checks intended email and organization, then creates membership atomically. Operations that could remove the final Owner fail with `conflict` even under concurrency. Organizations are not mixed in a single list response unless the user has membership in each returned tenant.

## Cross-tenant vectors

- Given a valid Owner session for organization A and an application ID in B, `GET/PATCH` under A returns `not_found_or_hidden` and does not reveal B’s existence.
- Given a valid key for environment A, Analyze/Gateway requests specifying B’s application/environment fail authentication/scope validation before analysis.
- Given a queued incident job whose event was moved, deleted or no longer belongs to its declared organization, worker rejects the job without side effect and records a safe failure.
- Given a concurrent attempt to remove both remaining Owners, at most one transition may commit; the organization retains an Owner.

PostgreSQL RLS remains a deferred defense-in-depth option per [Phase 2](../phase-02/10-auth-tenancy-security-architecture.md); server RBAC and scoped queries are the V1 baseline.
