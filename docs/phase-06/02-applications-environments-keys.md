# Applications, environments, and keys

`Application` is directly tenant scoped, UUIDv7 identified, active/archived, and unique by case-folded name within an organization. Its privacy defaults are `REDACTED`, safe-content persistence off, and 30-day security retention. Archive is explicit and rejects later machine traffic and key issuance.

`Environment` carries organization and application IDs with a composite foreign key. One `development`, `staging`, or `production` row may exist per application; status is `active` or `disabled`. The redundant organization ID is intentional database enforcement of ancestry.

Application keys use `rz_<env>_<lookup>_<secret>`: `env` is `dev|stg|prd`, lookup is 128 random bits in 22-character unpadded base64url, and secret is 256 random bits in 43-character unpadded base64url. The database stores lookup, visible prefix, HMAC verifier, verifier key ID, scope, lifecycle timestamps, and label—never the full key or secret. The application-key verifier root is separately configured from the session verifier root. Verification parses exact lengths, performs constant-time comparisons, and treats stored scope as authoritative. Rotation issues a new one-time secret and revokes the old key in the same transaction.

Management routes follow the Phase 3 catalog. Readers can read applications/environments; Owner/Admin/Developer can mutate names, environments, and keys; only Owner/Admin may change privacy/retention. All queries include the server-derived tenant predicate. Key creation/rotation responses are intentionally not idempotently replayed.
