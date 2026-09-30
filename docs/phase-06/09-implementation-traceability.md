# Phase 6 implementation traceability

| Requirement | Implementation seam | Verification |
|---|---|---|
| FR-013–014, US-005 | Application/Environment models, services, APIs, console | lifecycle, uniqueness, isolation, archive/disable tests |
| FR-015–019, US-006/027 | dedicated key crypto, verifier-only model, management APIs | format, storage, invalid/expired/revoked/rotation tests |
| FR-020 | Analyze API and shared AnalysisService | authenticated API and offline engine tests |
| FR-021 transitional detection fields | finding response plus explicit Phase 7 capability markers | contract asserts no fake risk/action |
| FR-022–026 | registry’s eleven categories/twelve stable IDs | per-detector and corpus tests |
| FR-027 | direction-aware output secret/PII rules | output privacy corpus/API tests |
| FR-028 detection/redaction slice | typed redaction and safe evidence | overlap/privacy tests; policy-triggered redaction deferred |
| NFR-001 | timing instrumentation and benchmark test | short/medium/max measurements |
| NFR-006 | separate keyed verifier root, no plaintext storage | crypto/storage assertions |
| NFR-010 | framework-free security domain and layered tests | architecture/unit/API/integration/frontend suites |
| NFR-015 | 32 KiB default and 128 KiB hard ceiling | byte-bound tests/config validation |
| SEC-002/011/018 | one-time secret, immediate lifecycle checks, constant-time compare | key lifecycle tests |
| SEC-004 | server-derived tenant queries and composite foreign keys | cross-tenant API/live PostgreSQL tests |
| SEC-007/010/023/025 | bounded normalization, redacted telemetry/storage, limitations | normalization/privacy/scans/docs |
| SEC-016 | keyed Redis Analyze limiter | unit failure and live Redis integration |

FR-029 and later risk/policy requirements and FR-044 and later Gateway requirements are not marked implemented. Relevant stories covered are US-005–008, US-010–012, US-027–029, limited strictly to detection-era acceptance.
