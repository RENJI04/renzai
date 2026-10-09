# Security and supply-chain audit

The history secret scan covered ten reachable commits with Gitleaks. Its three generic-key
candidates are a synthetic Bruno idempotency key, a synthetic cross-tenant test key, and API-key
contract prose—not credentials. Environment templates use explicit `replace-*` or
`development-only-*` markers; actual environments are ignored. The final patch security review
found no reportable finding. The current-tree and reachable-history privacy scans confirm the
legacy private verifier email literal was removed as described in the
[privacy audit](04-privacy-and-history-audit.md).

Python `pip-audit` against `requirements.lock` reported no known vulnerabilities. The pnpm
audit initially identified high-severity production dependency advisories in Next.js, sharp, and
source-map-js. The candidate updates Next.js and eslint-config-next to 16.3.8 and constrains
sharp to 0.35.5 and source-map-js to 1.2.2. The final production pnpm audit reports no known
high-severity vulnerabilities. One advisory for `braces` remains in the ESLint-only development
dependency chain; the registry has no 3.0.4 patch available at this audit time. It is not shipped
in the runtime web image, and no untrusted glob patterns are fed to ESLint in CI. This exception
must remain visible to maintainers and be re-evaluated when a patch is published.

The CI workflows grant read-only contents permission by default. The pnpm workspace explicitly
denies the unapproved `unrs-resolver` postinstall script. The security workflow formerly
referenced `aquasecurity/trivy-action@0.33.1`, a version family covered by the maintainer's
March 2026 supply-chain advisory. It now pins the post-remediation v0.36.0 commit by full SHA.
Other Actions use moving major-version tags and remain a maintenance consideration. A first
local image scan found fixable high/critical findings in the older Python base image. Updating
the Debian base removed every fixable high/critical finding, but the full Grype feed still
reported unfixed distribution findings. The API and worker therefore moved to the official
Python 3.13.16 Alpine 3.23 image and apply the available Alpine package upgrade in the runtime
stage. The rebuilt API and worker scans each report five medium findings and no high/critical
findings; the web scan reports three medium findings and no high/critical findings. The images
run as their documented unprivileged users, the rebuilt Compose stack passed the full smoke
verification, and final SPDX JSON SBOMs were generated locally. No registry publication is
authorized.

The final Python dependency audit reports no known vulnerabilities. The final production pnpm
audit also reports no known vulnerabilities. The full development audit still reports one high
`braces` advisory in the ESLint-only dependency chain described above. These audit results are
time-specific and must be repeated for a later publication candidate.
