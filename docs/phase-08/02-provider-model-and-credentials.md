# Provider model and credentials

`ProviderConfiguration` belongs to exactly one organization/application/environment ancestry and uses a UUIDv7 primary key. Supported kinds are `openai_compatible_remote` and `openai_compatible_local`; status is `active` or `disabled`. A normalized name is unique per environment. The table stores base URL, configured model, declared seed capability, token/timeout/response limits, validation state, ciphertext and key ID. It has no plaintext credential column.

Credentials use application-level AES-256-GCM from `cryptography`. Each encryption uses a random 96-bit nonce. A SHA-256 purpose derivation produces a provider-specific 256-bit key from each configured root, and authenticated additional data binds ciphertext to purpose, organization, application, environment, and provider. Roots must be at least 32 UTF-8 bytes; session-verifier and application-key roots are rejected as provider roots, and staging/production reject development placeholders.

The key-ring interface has an active write key ID and a set of readable keys. New credentials use the active key; old ciphertext remains readable through its stored key ID, providing the rotation seam without claiming automated bulk re-encryption. Unknown keys, altered ciphertext, or context mismatch fail as configuration errors. Plaintext exists only while accepting a secret or immediately before outbound authorization construction. API responses expose only `credential_present` and `credential_key_id`; audit metadata never includes secret or ciphertext.

Owner and Admin may create, update, enable, disable, and validate providers. Security Analyst and Developer may view masked configuration but cannot administer credentials.
