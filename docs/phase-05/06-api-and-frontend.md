# API and frontend surface

Implemented auth endpoints: register, login, logout, session bootstrap, password change, reset request/confirm, and verification request/confirm. Implemented organization endpoints: create/list/get/update, member list/update/delete, invitation create, and token acceptance. All are under `/api/v1`; errors retain the stable Renzai envelope and request ID.

The Next.js console performs same-origin API calls with credentials and request IDs. It supports account registration/login, session bootstrapping, organization creation and switching, role-aware member display and invitation, verification request, and logout. The UI stores no session or CSRF secrets in local/session storage. TanStack Query owns ephemeral server state.

The session bootstrap returns current memberships and the CSRF token. The organization list remains the authoritative source for current tenant names and roles. The UI hides management controls for non-admin roles, while the backend always enforces authorization independently.
