# Phase 15A scope

Phase 15A converts the existing functional frontend into a coherent security
operations product without changing the frozen Phase 1-14 backend, database,
contracts, authentication, authorization, analysis, Gateway, incident,
analytics, AI Intelligence, or SDK behavior.

The previous interface exposed most tasks in one long developer-oriented page.
That made overview metrics compete with onboarding, configuration, incidents,
and account operations. Phase 15A separates those tasks into navigable product
surfaces, introduces a persistent application shell, and establishes a shared
visual and interaction system.

The work is intentionally frontend-only. UI role checks improve affordances but
do not replace server-side RBAC. All content, decisions, metrics, and mutations
continue to use existing API responses and semantics. No migration or backend
file was changed, no unsupported capability was added, and no Phase 15B
observability or deployment work was started.
