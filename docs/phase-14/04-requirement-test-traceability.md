# Requirement-to-test traceability

This matrix maps implemented V1 requirement groups to primary executable evidence. Deferred Phase 1
requirements remain deferred; tests do not claim their implementation.

| Requirement/contract group | Primary evidence | Layer | Status |
| --- | --- | --- | --- |
| FR-001–006; SEC-001,003,005,017,024; auth/session contract | `test_identity_tenancy.py`, `test_phase13_security_hardening.py` | API E2E/security | Covered |
| FR-007–012; SEC-004,015; tenancy/RBAC | identity, Phase 9, Phase 11, Phase 13 RBAC tests | API/service/PostgreSQL | Covered |
| FR-013–019; key lifecycle | `test_phase6_api.py`, Phase 6 PostgreSQL integration | API E2E/database | Covered |
| FR-020–028; deterministic security | `test_security_engine.py`, V1 corpus, Phase 14 replay | unit/corpus/E2E | Covered |
| FR-029–030; risk | `test_risk_policy_domain.py`, `test_phase7_api.py` | unit/API | Covered |
| FR-031–033; policy | risk/policy domain, Phase 7 API, priority race | unit/API/PostgreSQL | Covered |
| FR-034–036; incidents | `test_phase9_api.py`, Phase 9 integration | API E2E/PostgreSQL | Covered |
| FR-037–040; analytics/dashboard | `test_phase10_api.py`, Phase 10 PostgreSQL integration, frontend dashboard tests | API/database/component | Covered |
| FR-041–043; providers/AI intelligence | Phase 8 provider tests, Phase 11 tests, worker tests | API/security/worker | Covered |
| FR-044–046; Gateway | Phase 8 API/HTTP tests and Phase 9 escalation tests | API E2E/failure | Covered |
| FR-047–048; audit/retention implemented surfaces | identity/tenant audit, incident retention tests | API/PostgreSQL | Covered |
| FR-049–050,056; notifications/webhooks | Phase 1/3 future scope | — | Deferred, not implemented |
| FR-051–053; privacy/retention | Phase 6, 9, 10, 11 privacy and retention tests | API/PostgreSQL | Covered |
| FR-054–055; health/readiness/docs | `test_app.py`, config/security tests | contract | Covered |
| NFR-001,010,015; bounds/performance/determinism | security engine, body limits, benchmarks | unit/API/measurement | Covered |
| NFR-002,006,014; provider failure/availability | provider adapter, Gateway and AI failure tests | unit/API | Covered |
| NFR-003–004,009; async/database/worker | live PostgreSQL and worker claim tests | integration/concurrency | Covered |
| NFR-005,007; identity usability/security | identity API and frontend identity tests | API/component | Covered |
| NFR-008,011; safe operations/analytics | errors/logging, dashboard tests | contract/API | Covered |
| NFR-012; deployment/self-hosting | deployment implementation is later work | — | Deferred |
| NFR-013,016; maintainability/versioned API | architecture tests, both SDK suites, compatibility verifier | contract/package | Covered |
| SEC-002,011,018; API-key secrecy | key crypto/lifecycle, SDK header/repr tests, Redis key test | unit/API/live | Covered |
| SEC-007,010,016,025; security engine/policy | detector, risk, policy, redaction tests | unit/API | Covered |
| SEC-008–009,024; safe errors/logging | error matrix, logging and security-header tests | contract/component | Covered |
| SEC-012–014,019–022; provider/SSRF/crypto | provider security/HTTP tests, AI credential tests | unit/local HTTP | Covered |
| SEC-023; tenant privacy | cross-tenant API and composite-FK tests | API/PostgreSQL | Covered |

The frozen Phase 3 error contract uses 422 for bounded parse/validation failures; HTTP 400 is not a
Renzai-owned V1 error mapping and is therefore not invented for Phase 14.
