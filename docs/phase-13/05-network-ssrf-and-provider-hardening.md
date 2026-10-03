# Network, SSRF, and provider hardening

The shared outbound guard continues to reject userinfo, fragments, unsafe schemes, loopback,
unspecified, private, link-local, multicast, reserved and IPv4-mapped private addresses. Every DNS
answer is checked. The connection is made to a validated numeric address while retaining the
validated Host header and TLS SNI. Redirects and environment proxies are disabled. Remote provider
mode requires HTTPS; HTTP/private targets require local-provider mode and an exact configured host.

Phase 13 startup validation rejects wildcard, CIDR, URL-like, whitespace/control-containing, empty,
or oversized local-host allowlist values. Values such as `*` and `0.0.0.0/0` cannot silently turn
the exception into a private-network wildcard. The allowlist is an explicit operator trust boundary,
not an SSRF bypass intended for tenant input.

The pinned HTTP response parser now rejects duplicate Content-Length, duplicate Transfer-Encoding,
simultaneous Content-Length plus Transfer-Encoding, unsupported transfer encodings, and invalid
header names/values. Provider and AI bodies remain bounded during accumulation, not after an
unbounded read. Public errors never include provider bodies.

Credential encryption remains AES-256-GCM with fresh nonces and purpose-separated AAD containing
tenant and configuration identities. Gateway and AI contexts cannot decrypt one another; tampering
fails closed; key IDs support old-key read/new-key write rotation; ciphertext and plaintext are not
returned. AI configuration request credentials now use Pydantic `SecretStr` until the application
service boundary, reducing accidental representation leakage.

No network protocol or provider capability was added.
