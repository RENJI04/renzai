# Renzai v1.0.0 release-candidate review

Phase 17A local preparation is complete and the release candidate is safe to publish pending
explicit owner approval. The ten-commit author/committer privacy rewrite and the narrowly scoped
content-history remediation are complete and verified. Apache License 2.0 was explicitly approved,
application version metadata is reconciled, and release notes and changelog are prepared locally.

The authorized content-history rewrite removed the legacy private verifier email literal from the
current candidate and all reachable history while preserving unrelated history. The rebuilt-image
scans found no high or critical findings, local SBOMs and artifact checksums were generated, and
the final patch security review found no reportable finding. The clean-room Quick Start and
application test matrix passed. A development-only dependency advisory without a published patch
is documented in the [supply-chain audit](05-security-and-supply-chain-audit.md) and must remain
visible. These checks do not certify a production deployment.

The Phase 15B and Phase 16 asset verifiers, focused release regressions, Git whitespace checks,
current-tree and reachable-history privacy scans, artifact inspection, and checksum verification
passed after the final release-document updates. The source archive and checksum manifest remain
local until publication is explicitly approved.

No commit, push, tag, remote, GitHub repository or release, image, PyPI, or npm publication occurred
in Phase 17A. Separate Phase 17B authorization is required even if every local gate passes.
