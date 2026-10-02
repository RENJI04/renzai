# AI provider and credentials

AI configurations are distinct from Gateway provider configurations and can be organization-, application-, or environment-scoped. The most-specific single active configuration is selected; ambiguity fails safely. Owner/Admin can create, update, enable, disable, and validate configurations. Reads return masked metadata only.

Credentials use AES-256-GCM with authenticated tenant/config context and the dedicated `renzai/ai-intelligence-credential/...` cryptographic purpose. Plaintext, ciphertext, and key identifiers are absent from API responses, prompts, logs, audit metadata, and broker messages.

Credential input rejects HTTP control characters before encryption, and the provider adapter repeats that validation after authenticated decryption before constructing an Authorization header.

The OpenAI-compatible adapter reuses the Phase 8 IP-pinned, proxy-independent transport and target guard. Remote targets require HTTPS and reject loopback, private, link-local, multicast, unspecified, reserved, metadata-style, and IPv4-mapped private destinations. Redirects and oversized responses fail safely. Local endpoints require exact operator allowlisting.
