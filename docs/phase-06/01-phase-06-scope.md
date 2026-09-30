# Phase 6 scope

Phase 6 implements deterministic detection and the minimum machine-scoped resources needed to invoke it. It includes Applications, Environments, environment API keys, `POST /api/v1/analyze`, the session-authenticated Security Playground, normalization, all V1 detector categories, finding aggregation, privacy-filtered persistence, rate limiting, tests, and implementation evidence.

The phase deliberately ends before risk scoring and policy evaluation. Successful responses expose `capabilities.risk_scoring.evaluated=false` and `capabilities.policy.evaluated=false`; they do not fabricate `risk_score=0` or `action=allow`. “Safe” and “no detected threat” mean only that a complete detector pass returned zero findings.

No gateway forwarding, provider call/configuration, AI intelligence, policy CRUD, baseline policy, incident lifecycle, notification, webhook, analytics dashboard, SDK, or tool execution is present. Phase 7 owns the risk/policy slice.
