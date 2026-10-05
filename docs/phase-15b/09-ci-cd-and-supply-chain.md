# CI/CD and supply chain

`ci.yml` runs backend lint, format, typing, tests, live disposable PostgreSQL/Redis integration, frontend checks and build, Python 3.11/3.13 SDK checks, TypeScript SDK checks, Compose validation, and all three production image builds. Jobs use explicit timeouts, dependency caches, concurrency cancellation, and read-only repository permissions.

`security.yml` performs pull-request dependency review, Trivy filesystem vulnerability/secret/misconfiguration scanning, per-image HIGH/CRITICAL scans, and SPDX JSON SBOM generation. Dependabot covers pip, npm, GitHub Actions, and Docker dependencies. These checks reduce risk; they do not prove absence of vulnerabilities or provide certification.

Third-party actions use stable major or explicit release tags. Higher-assurance deployments should pin reviewed commit SHAs through an automated update policy. No `pull_request_target` workflow exists, untrusted pull requests receive no repository secrets, and Phase 15B does not publish packages or images.
