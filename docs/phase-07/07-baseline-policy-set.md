# Baseline policy set

Every application receives nine explicit, visible, enabled application policies:

| Phase | Match | Priority | Action | Purpose |
| --- | --- | ---: | --- | --- |
| input | critical | 100 | block | strongest input risk |
| input | high | 200 | require_review | surface human review semantics |
| input | medium | 300 | flag | retain a non-blocking warning |
| input | low | 400 | allow | explicit benign baseline |
| output | secret exposure | 50 | redact | remove validated secret spans first |
| output | critical | 100 | block | critical output risk without safe secret redaction |
| output | high | 200 | require_review | explicit review result |
| output | medium | 300 | flag | retain output warning |
| output | low | 400 | allow | explicit benign baseline |

New-application bootstrap is in the application transaction and idempotent by baseline key. Migration `20260927_0003` deterministically backfills existing applications and seeds the global profile. Baselines use normal versioning thereafter and remain visible. Disabling/archiving them preserves P3-001: no match still means allow.
