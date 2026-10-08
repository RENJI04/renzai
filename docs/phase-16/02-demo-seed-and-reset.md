# Demo seed and reset

`scripts/prepare_demo_env.py` creates random, untracked loopback settings. `compose.demo.yaml` is an
explicit development-only override; production `compose.yaml` and its validation gate remain
unchanged. After a user registers `analyst@demo.invalid`, `scripts/seed_demo.py` creates the dedicated
**Renzai Demo Lab** tenant.

The deterministic dataset contains three applications, nine environments, 28 time-distributed
metadata-only analyses, all eleven categories, baseline policies, disabled credential-free synthetic
providers, eight Gateway provider-call metadata records, eight incidents across all five statuses,
evidence/timeline/comments, and one explicitly synthetic historical advisory result. Stable UUIDv5
identities make repeat runs idempotent; no password, API key, session, provider credential, personal
identity, or raw prompt is seeded.

`scripts/reset_demo.py` requires the exact name, slug, marker, and synthetic-content marker. It deletes
only rows reached through that organization and leaves the registered user and unrelated tenants
untouched. Missing data is an idempotent no-op; a reserved-slug collision is refused. Automated tests
cover seed → duplicate seed → reset → reset → seed and ambiguous-target refusal.
