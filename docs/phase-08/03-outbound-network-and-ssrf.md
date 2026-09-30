# Outbound networking and SSRF controls

Remote provider URLs require HTTPS. URL parsing rejects userinfo, fragments, queries, unsupported schemes, malformed hosts, control characters, metadata-style hostnames, and unsafe addresses. Every DNS answer is checked; loopback, RFC1918/private, link-local, multicast, unspecified, reserved/non-global, IPv4-mapped IPv6 equivalents, and cloud-metadata-like destinations are denied.

The adapter does not validate a hostname and then ask a generic client to resolve it again. It connects a low-level HTTP/1.1 client directly to one already-validated address while retaining the original hostname for TLS SNI and `Host`. All returned addresses must pass validation before one is selected. Proxy environment variables are never consulted.

V1 follows no redirects. Any 3xx response is a provider error, so authorization is never inherited to a redirect target. The configured redirect limit is zero. Responses have bounded headers and bodies, no response decompression, explicit connect and total timeouts, and no automatic completion retry.

Local provider access is an explicit provider kind plus an exact trusted-host allowlist. It is not inherited by remote providers or future webhook behavior. The local exception is hostname-exact; it is intended for operator-selected self-hosted endpoints such as Ollama. The guard is process-local network policy rather than a substitute for host firewall/egress controls, and DNS can still change between separate requests; each request resolves and validates again.
