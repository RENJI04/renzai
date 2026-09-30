# Policy precedence and actions

For the current phase, enabled active policies are evaluated independently in organization, application, and environment scope. Ascending priority is authoritative and the first match wins in each scope.

At most three winners are combined by `block > require_review > redact > flag > allow`. Equal actions select the more specific environment, then application, then organization scope. All scope winners and evaluated versions are recorded, so a narrower allow cannot weaken a stronger parent.

With successful inspection/risk and no match, P3-001 returns `allow`, null match, empty winners, and `no_policy_matched`. Analyze returns successful objects for all five actions. `require_review` does not wait; `block` is not HTTP 403. Evaluation/redaction failure is an explicit `inspection_failure`.
