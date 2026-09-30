# Frontend development

`apps/web` is a strict TypeScript Next.js application. The Phase 5 console supports registration/login, session bootstrap, organization creation/switching, role-aware member viewing/invitation, verification requests, and logout.

TanStack Query has short stale time and no persistence. The same-origin client includes cookies, request IDs, and CSRF headers and parses stable error envelopes. No authentication or CSRF token is written to browser storage. Next rewrites `/api/*` to `RENZAI_API_ORIGIN` (default `http://localhost:8000`).
