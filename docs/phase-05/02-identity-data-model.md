# Identity data model

The Phase 5 identity model comprises `users`, `password_credentials`, `sessions`, `password_reset_tokens`, and `email_verification_tokens`. User identity is global; credentials are private to auth. Normalized email is globally unique, password material is Argon2id-only, and all bearer credentials use random lookup plus keyed verifier storage.

UUIDv7 is used for entity identifiers. Session records include idle and absolute deadlines, revocation, last activity, CSRF verifier, verifier key ID, and privilege version. Reset and verification records include expiry and one-time consumption timestamps. Full field and security rationale is in [identity and session design](02-identity-and-session-design.md).
