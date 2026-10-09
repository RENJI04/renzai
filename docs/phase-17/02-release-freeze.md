# Release freeze

The local release branch is `main`; the committed Phase 16 baseline before Phase 17A was
`667e5546408dfa6ab8e7105a64b2dc6a590f7b67`. The owner explicitly authorized a local,
identity-only rewrite of its ten reachable commits because the former author/committer email was
private. The rewritten baseline is `9027696c90756bfd783561f9f4140853443fcfa6`. Commit
order, trees, messages, and author/committer timestamps were verified equal pairwise.

Phase 17A source changes remain uncommitted pending the final audit and owner review. A private
recovery bundle exists outside the repository; it must never be included in a public release.
No remote is configured. No push, tag, repository creation, GitHub Release, or package/image
publication is authorized by this phase.

Release-freeze exceptions are limited to verified privacy/secret/security findings, packaging
defects, reproducibility problems, and documentation or version drift. Historical migrations are
unchanged.
