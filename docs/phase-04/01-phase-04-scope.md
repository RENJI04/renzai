# Phase 4 scope

Phase 4 is the first implementation phase and is restricted to project foundations. It implements app/factory, configuration, async database/Redis/Celery seams, safe errors/logging/request context, operational endpoints, package boundaries, development tooling, frontend shell and tests. [Phase 1](../phase-01/12-phase-01-review.md), [Phase 2](../phase-02/18-phase-02-review.md) and [Phase 3](../phase-03/21-phase-03-review.md) remain respectively product, architecture and contract authority.

Authentication, sessions, RBAC, tenant/application/key persistence, detectors, scoring, policy evaluation, providers, Gateway, incidents, notifications, webhooks, AI analysis and dashboard behavior are deliberately deferred. No fake endpoint substitutes for them.

Future Phase 7 policy note: because a valid inspection with no matching policy allows traffic, a new installation will need a reviewed seeded baseline policy set before the policy engine is usable. The candidate direction is critical→block, high→require-review or block after review, medium→flag, low→allow, and output secret leakage→redact/block. This is documentation only—not a policy implementation or approved final rule set.
