# Policy suggestion workflow

AI policy output is parsed into a strict draft schema and then instantiated through the same Phase 7 `PolicyCondition` and `PolicySnapshot` grammar used by deterministic policy code. Unknown facts/operators, regex, nested values, invalid actions, excessive conditions, invalid redaction targets, and malformed groups are rejected.

No `Policy` or `PolicyVersion` is created by an AI request. The Incident UI labels output as a validated draft and directs operators to the normal policy workflow. It exposes no activate action. Any future draft import must retain normal policy-editor authorization and explicit create/activate steps.
