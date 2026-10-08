# V1 limitations

Renzai V1 intentionally has a narrow, inspectable boundary:

- Gateway is non-streaming and text-only; it does not implement full OpenAI compatibility.
- Tools/functions, multimodal input, generic agent security, autonomous remediation, notifications,
  and webhooks are not implemented.
- Deterministic rules have false-positive and false-negative tradeoffs and do not guarantee complete
  prompt-injection, jailbreak, PII, secret, or exfiltration prevention.
- Optional AI is advisory only and requires an operator-configured compatible provider.
- Baseline Compose publishes loopback HTTP, not production TLS. Operators own trusted ingress,
  certificates, network ranges, secret injection, capacity, upgrades, and incident response.
- The repository does not provide an automated production backup service, HSM/KMS certification,
  production SLA, formal compliance certification, external penetration-test certification, or
  formal WCAG certification.
- Python and TypeScript SDKs are local source packages; they are not published to PyPI or npm.
- Phase 17 must reconcile release versions, license, changelog, privacy/history, and publication.

These constraints keep the V1 contract clear. They are not promises of future implementation.
