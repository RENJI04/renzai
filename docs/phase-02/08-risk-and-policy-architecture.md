# Risk and policy architecture

## Versioned risk scoring

A scoring profile is a reviewed, immutable versioned configuration of detector contribution rules, severity weights, caps, combination rules, confidence semantics and severity thresholds. Its identifier and version are stored with each analysis result. Profile data is never overwritten in place after use; old results can be interpreted against the version that produced them. Rollout selects an explicit profile per environment or application and records the change in audit. A rollback selects a prior immutable profile rather than rewriting history.

The result is an integer 0–100, one severity band (Low, Medium, High, Critical), an explicitly defined confidence measure and a contribution breakdown. Aggregation must define overlaps and caps so duplicates do not inflate risk accidentally. Phase 3 will choose exact numerical weights and threshold values through a reviewed, version-controlled regression corpus. No hidden adaptive learning modifies enforcement. False Positive status does not alter a detector/profile; corpus promotion requires human review.

## Bounded declarative policies

Policy scope is organization-wide or narrowed to an application/environment. A policy has enabled state, phase (`input` or `output`), version, priority, bounded conditions and one action: allow, flag, block, redact, require review. Conditions may compare only approved structured facts such as category, severity, score range, confidence band, direction and context. Arbitrary expressions, scripts and network calls are excluded from V1 evaluation.

Evaluation is deterministic against one policy snapshot. Sort enabled matching policies by explicit priority and a stable tie breaker; the selected policy and rationale are returned and recorded. Phase 3 must specify the exact tie-break rule and whether highest priority wins versus a safer-action precedence in ties; no ambiguous policy may be accepted before then. A missing match follows a documented default action; the precise V1 default requires an explicit product decision because Phase 1 enumerates actions but does not choose a universal default. The architecture permits an organization baseline policy plus narrower application/environment rules, with precedence made explicit before implementation. This is a bounded open item, not a silent scope change.

Input `block` stops provider forwarding. Output `block` withholds provider text. `redact` applies typed replacements before returning/storing applicable content. `require review` must be represented as a safe enforcement outcome and incident/notification trigger; its transport behavior is specified with Phase 3 contracts. Policy changes create a new version and audit event, and active requests evaluate one consistent snapshot. An unsafe/invalid policy configuration is rejected, never interpreted as implicit allow.

## Trace and verification

Every decision record includes policy ID/version, scoring profile/version, detector versions, phase, matched condition summary, action and safe rationale. Planned verification: deterministic scoring vectors, historical profile replay, overlap/cap tests, policy precedence/tie tests, input/output action tests and privacy checks. No scoring or policy algorithm is implemented in Phase 2.
