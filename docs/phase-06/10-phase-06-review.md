# Phase 6 review

Phase 6 adds the complete deterministic detection slice over the Phase 5 identity boundary: minimal Applications/Environments, environment-scoped verifier-only keys, machine context, offline Analyze, versioned normalization, all V1 deterministic detector families, privacy-safe Findings, overlap aggregation, SecurityEvent/AnalysisResult/Finding persistence, privacy modes, Redis limiting, the regression corpus, instrumentation, and the minimal management/Playground UI.

The schema change is the additive `20260926_0002` revision. Composite foreign keys enforce organization → application → environment ancestry for environments, keys, and events. Key verification uses a dedicated root and exact format parser. Analysis persistence is atomic and records all reproducibility versions. The browser never receives a machine key for Playground; one-time management secrets live only in local component state and clear on dismissal or scope navigation.

Security review focuses on raw key/content logging, evidence leakage, browser storage, cross-tenant scope, bounded decode/regex behavior, and phase-boundary drift. Known detector limitations include language/semantic paraphrases, incomplete homoglyph handling, conservative encoded-content redaction, and inevitable deterministic false positives/negatives. These controls reduce risk but cannot guarantee harmless content.

Risk scoring, risk contributions/profiles, policy evaluation/CRUD/baselines, action decisions, gateway/provider behavior, incidents, notifications, analytics, SDKs, and tool authorization remain deferred. The UI states this explicitly and responses contain no fabricated Phase 7 values.

Final quality gates passed on 2026-09-26: 61 backend tests with live PostgreSQL and Redis, PostgreSQL migration round-trip and schema-drift verification, Ruff formatting/lint, mypy, Prettier, ESLint, TypeScript, 6 web tests, and an optimized Next.js build. Repository scans found no production browser storage for application keys, no network/provider calls in the detector domain, and no raw application-key or prompt-content logging path.
