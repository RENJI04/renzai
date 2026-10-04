# Defects and test-gap register

## Defects

| ID | Symptom and root cause | Reproduction | Minimal fix | Affected contract | Status |
| --- | --- | --- | --- | --- | --- |
| P14-01 | Critical workspace fields relied on placeholders and loading/reset feedback lacked live-region semantics | Frontend identity accessibility test | Added programmatic names and polite status roles; no visual/workflow redesign | Frontend accessibility/usability | Fixed |
| P14-02 | Provider list query loading, empty, and failure states were not rendered; query errors could remain invisible | Provider-manager state test | Added bounded status, empty text, and safe alert rendering | Frontend error/loading/empty behavior | Fixed |

No detector, risk, policy, Gateway, incident, analytics, AI, SDK, schema, or migration behavior was
changed by these fixes.

## Test gaps

| Gap | Classification | Rationale / control |
| --- | --- | --- |
| HTTP 400 Renzai-owned envelope | Not applicable | Frozen Phase 3 maps bounded parse/validation to 422; no new 400 contract invented |
| Full browser matrix and formal WCAG audit | Deferred | Component semantics and real Next/API rewrite are tested; certification/cross-browser lab is separate work |
| Real paid provider behavior | Not applicable | External providers are prohibited; deterministic local boundaries cover the protocol |
| Notifications/webhooks/SIEM | Deferred | Not implemented in V1 frozen scope |
| Production-scale load/soak and SLA | Deferred | Existing benchmarks are local regression measurements, not production claims |
| External penetration test/HSM/KMS/compliance | Deferred | Deployment/release assurance, not Phase 14 test code |
| Registration enumeration behavior | Accepted | Phase 13 documented contract limitation; changing it requires explicit product authorization |
| Project license | Deferred release blocker | Must be solved in Phase 17, not Testing |
