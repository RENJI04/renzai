# Phase 13 security review

## Result and severity method

Phase 13 completed a cross-cutting hardening pass from baseline
`39ff2a31185caab3a3a5836836eda768e81e9ddd` without a migration or product-scope expansion.
Severity is qualitative: impact (tenant/secret/enforcement/availability), exploitability, required
access, and whether an existing boundary reduces reach. No CVSS score was invented.

## Findings register

| ID | Surface | Severity | Status | Evidence / abuse case | Fix and regression | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| P13-01 | Session fixation | Medium | confirmed-fixed | Login accepted a valid presented session without revoking it | Row-lock/revoke before new session commit; old-cookie regression | Concurrent independent sessions remain intentional |
| P13-02 | Opaque credentials | Low | confirmed-fixed | Unbounded malformed lookup strings could reach parsing/lookup | Exact bounded base64url shape; parser tests | None known |
| P13-03 | Mass assignment | Low | confirmed-fixed | Auth/organization inputs accepted unknown fields | Strict request models including Analyze; 422/model regressions | Response models remain additive by contract |
| P13-04 | Request resource use | Medium | confirmed-fixed | Most JSON routes had no pre-parser body ceiling | General and route-specific streaming body middleware; oversize test | Proxy-level limit is operator responsibility |
| P13-05 | Session mutation abuse | Medium | confirmed-fixed | Cookie-authenticated writes lacked a shared required limiter | Keyed per-session Redis limiter, fail closed; boundary test | Logout can be unavailable with required Redis outage |
| P13-06 | Configuration | Medium | confirmed-fixed | Production allowed debug/docs and loose CORS/local-host values | Startup rejection and configuration regressions | Trusted-proxy/network policy remains deployment work |
| P13-07 | Provider HTTP parsing | Medium | confirmed-fixed | Conflicting/duplicate framing could be interpreted ambiguously | Strict framing/header checks; three regressions | HTTP/1.1 only by design |
| P13-08 | Logging | Medium | confirmed-fixed | Nested sequence secrets and control/large paths were not fully sanitized | Recursive redaction and bounded control-safe path tests | Novel semantic secret keys require vocabulary maintenance |
| P13-09 | Browser/cache | Medium | confirmed-fixed | No explicit CSP/frame denial or sensitive API no-store | API/Next headers and integration tests | CSP retains required inline style/script allowance |
| P13-10 | AI credential input | Low | confirmed-fixed | Plain request strings had a larger accidental repr surface | `SecretStr` to service boundary; existing ciphertext tests | In-process plaintext is necessary for encryption/provider use |
| P13-11 | SDK request construction | Medium | confirmed-fixed | Tabs/NUL/space or parser-normalized URLs could reach HTTP headers/origin | Bounded visible-ASCII headers and pre-parse URL checks in both SDKs | HTTP development base URLs remain supported |
| P13-12 | Python dependencies | High | confirmed-fixed | Audit found `cryptography 46.0.7` below multiple security fixes; pytest dev advisory | Upgrade constraints/lock; tests and clean `pip-audit` | Future advisories require routine scanning |
| P13-13 | Account enumeration | Low | accepted-limitation | Registration returns Phase 3 catalog conflict for existing email | No silent contract break; documented | Requires explicit future contract decision |
| P13-14 | Operator comments | Low | not-reproducible | Stored XSS/log/secret propagation reviewed | React text rendering, bounded field, no comment logging | Future integrations must not export blindly |
| P13-15 | Live service verification | Medium assurance gap | deferred-with-reason | Docker engine did not answer version queries; service ports unavailable | Unit/SQLite suites retained; integration tests remain opt-in | PostgreSQL locks/FKs and Redis behavior need a reachable engine |
| P13-16 | External assurance/key custody | Low | accepted-limitation | No external penetration test, HSM/KMS, or compliance assessment | Explicit deployment limitation | Required before higher-assurance claims |

No confirmed high or critical code finding remains unresolved. P13-15 limits assurance, not the
implemented control, and must be closed before a public v1.0 security sign-off.

## Verification summary

- Backend static gates: Ruff check/format and strict mypy pass.
- Focused hardening/RBAC/config/logging/provider tests pass; full pytest reports 253 passed and the
  nine explicitly configured live-service tests skipped because PostgreSQL/Redis were unavailable.
- Frontend: Prettier, ESLint, TypeScript, Vitest, and Next production build pass (one concurrent-load
  timeout was non-reproducible; isolated full Vitest passed 17/17).
- Python SDK: Ruff, mypy, and 28 tests pass. TypeScript SDK: Prettier, ESLint, TypeScript, build, and
  24 tests pass. Phase 12 local compatibility passes for both.
- Dependency audits: updated Python lock and production Node tree report no known vulnerabilities.
- Package and secret scans found no packaged or tracked real secret.
- Local benchmarks completed for risk/policy, Gateway, incidents, AI overhead, maximum Analyze,
  candidate-heavy normalization, and 32-message Gateway inspection. Results are measurements, not
  production SLAs.

## Known limitations and release blockers

Regex-based detection/PII scrubbing is best effort. Explicit local provider hosts are operator-
trusted. Single-node development assumptions are not production hardening. There is no HSM/KMS,
external penetration test, or certification. Forwarded-header trust, TLS termination, database and
Redis network isolation, backup protection, and root-key custody belong to deployment. The live
PostgreSQL/Redis assurance gap must be rerun when Docker/service access is restored.

The repository still has no project license file, which is a public open-source v1.0 release blocker
outside Phase 13. The registration-enumeration contract decision and live database/Redis verification
should also be resolved before release. Phase 14 has not started.
