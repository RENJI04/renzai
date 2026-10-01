# Incident escalation rules

The authoritative automatic use case consumes a committed analysis and never reruns detection, risk, or policy. Phase 3 explicitly requires durable Gateway escalation for `block` and `require_review`; those are the automatic Phase 9 triggers for input and output. `allow` is quiet. Phase 3 does not define unconditional automatic incident creation for `flag` or `redact`, so Phase 9 does not invent it; operators can create a manual incident.

`AnalysisService.analyze()` commits the event, analysis, findings, risk contributions, and policy decision before returning—or before raising its post-commit redaction failure. Gateway order is therefore:

1. inspect and durably commit the input analysis;
2. create and commit a required input incident;
3. enforce block/review or select a provider;
4. perform the provider call outside the incident transaction;
5. inspect and durably commit output analysis;
6. create and commit a required output incident;
7. record the provider-call outcome, then enforce/return.

Incident persistence failure is fail-closed. Input is never forwarded; output provider content is never returned, and the provider-call outcome is `output_inspection_failure`. Existing block/review HTTP semantics remain 403 `policy_block` and 409 `review_required`.

Analyze returns its decision and does not auto-create an incident. The authenticated manual API is the explicit Analyze escalation path in Phase 9; no reviewer workflow is created.
