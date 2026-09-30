# Frontend architecture

Next.js/React/TypeScript form the dashboard. Tailwind CSS and shadcn/ui provide presentation primitives; Recharts renders aggregate charts; TanStack Query handles client-side cache and mutations. Browser role visibility is convenience only; FastAPI enforces every permission.

## Proposed feature layout

```text
web/
  app/                 route shells and server-rendered entry views
    (public)/          login, register, reset
    (org)/             organization-scoped dashboard and feature routes
  features/
    auth/ organizations/ applications/ keys/
    analyze/ policies/ incidents/ logs/
    playground/ providers/ notifications/ audit/
  shared/
    api/               typed boundary client and safe error mapping
    ui/                design primitives
    context/           current organization/application/environment
```

This is a folder proposal only; no frontend files are created in Phase 2.

## Route and rendering strategy

Public routes support account creation and recovery. Organization-scoped routes host overview/dashboard, applications and environments, keys, logs, incidents/detail, policies, playground, providers, notifications and audit. A server-rendered route shell checks session state and initial organization access; interactive filters, charts, forms and incident timeline use client components. Sensitive provider credentials and application key secrets are never inserted into cached pages or serialized props except the one-time creation display to the authorized initiating user.

The browser sends same-origin, Secure/HttpOnly session cookies automatically. State-changing calls include a CSRF token or equivalent bound to the opaque session, with server validation. Session expiration or role changes invalidate sensitive cached views; the UI clears organization-scoped TanStack Query entries on logout or context switch. Do not store session credentials or provider secrets in local storage.

## Feature flows

| Flow | UI behavior | Backend authority |
|---|---|---|
| Organization/application/environment selection | Context picker changes route/query scope and clears dependent caches | Revalidates membership and object hierarchy for each request. |
| Dashboard | Server loads initial summary; client refreshes filters/graphs; charts use aggregates | Tenant-scoped analytics and privacy policies determine data. |
| Incident detail | Fetches safe findings/timeline, supports authorized comments/assignment/status | Revalidates roles, state transitions and assignee tenancy; audits changes. |
| Playground | Form validates size locally for feedback; displays detector outcomes, score/profile, policy rationale | Performs authoritative bounded validation and analysis; storage defaults apply. |
| Provider configuration | Shows masked config and explicit private-endpoint exception controls | Encrypts key, validates URL/DNS/IP and audits changes. |
| Policy management | Bounded condition editor, priority ordering, preview explanation | Validates declarative policy and evaluates authoritative outcome. |

Forms use typed client validation only for usability; backend Pydantic validation is authoritative. Safe errors show human message and correlation ID, never raw provider responses, secrets or stack traces. The UI labels AI-generated explanations and preserves deterministic evidence separately. Page and API caching must be partitioned by organization, user and permission state; no shared cache may expose cross-tenant responses. Exact route names, forms and response types belong to Phase 3 contracts.
