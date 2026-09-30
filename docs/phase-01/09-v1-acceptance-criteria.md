# High-level V1.0 acceptance checklist

A future V1.0 release is acceptable only when evidence demonstrates that an authorized user can:

- [ ] Clone the repository, configure a supported self-hosted environment, and start Renzai.
- [ ] Register, log in, create an organization, application, environment, and application API key.
- [ ] Submit a prompt for analysis and receive findings, risk, severity, confidence, explanation, and action.
- [ ] Detect common prompt-injection behavior without an external AI provider and enforce a policy.
- [ ] Create and investigate an incident; inspect organization-scoped logs and dashboard data.
- [ ] Use the Security Playground and inspect detailed detector results.
- [ ] Configure a supported OpenAI-compatible provider and obtain distinctly labelled AI incident analysis.
- [ ] Continue core deterministic operation when that provider is unavailable.
- [ ] Use the documented gateway subset to scan input and output, including secret/PII leakage handling.
- [ ] Review audit events, privacy storage behavior, retention behavior, RBAC, and tenant isolation.

This is a release-validation target, not evidence that the functionality exists in Phase 1.
