# Policy model and versioning

`Policy` is the mutable identity: tenant, exact organization/application/environment scope, phase, unique priority, enabled state, active version, and lifecycle status. `PolicyVersion` is an immutable configuration snapshot containing action, rationale, condition mode, conditions, and redaction targets.

Edits create a new inactive version. Activation selects it explicitly; rollback selects an older row without rewriting history. Analyses retain the exact evaluated and selected version IDs. Create, version creation, state changes, activation, rollback, archive, and application baseline bootstrap are audited without prompt or secret data.

Active profile versions and policy versions have no update route. The V1 profile is inspection-only. Archived policy identities release their effective priority; disabled non-archived identities do not.
