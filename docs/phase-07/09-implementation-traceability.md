# Implementation traceability

| Requirement | Implementation/evidence |
| --- | --- |
| FR-029, FR-030 | `modules/risk`, profile/version/contribution models, exact domain tests |
| FR-031, FR-032, FR-033 | `modules/policies`, management API, Analyze pipeline, policy UI/tests |
| SEC-004 | organization/application/environment ancestry and tenant-qualified FKs |
| SEC-014 | bounded grammar, no code/regex/external condition execution |
| SEC-015 | immutable version references and auditable state transitions |
| SEC-025 | typed redaction, privacy-separated persistence, fail-closed invalid target |
| NFR reproducibility | integer arithmetic, versioned snapshots, stored decisions/contributions |
| NFR performance | bounded 20-condition groups, first match per scope, explicit indexes/timing |

Gateway FR-044+, incident FR-034+, notifications, analytics, and provider execution are not marked implemented.
