# Authentication implementation

`IdentityService` implements registration, generic login failure, logout, current-password-verified password change, non-enumerating reset request, reset confirmation, and optional verification request/confirmation. The HTTP adapter owns cookies and origin policy; the application service owns transactions and lifecycle changes; framework-free user rules own normalization and password policy; crypto and persistence are adapters.

Password change rotates the current session and revokes all others. Reset revokes every session. Disabled accounts, revoked sessions, stale privilege versions, and expired deadlines fail authentication immediately. Development/test token return is an explicit mail-sink seam and is absent in protected environments.

`RENZAI_EMAIL_VERIFICATION_REQUIRED=false` keeps the verification lifecycle available but does not block tenant access. When true, organization creation/listing and tenant-context construction require a verified email. An outbound token-delivery protocol is present for a future SMTP/self-hosted adapter; no provider is configured in Phase 5.
