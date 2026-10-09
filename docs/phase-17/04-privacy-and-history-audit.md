# Privacy and history audit

The owner rejected the original private Git author/committer email for publication and expressly
authorized an identity-only local history rewrite. All ten reachable commits now have author and
committer `RENJI04 <255519538+RENJI04@users.noreply.github.com>`. The old identity is absent
from reachable commit metadata and tree content. The local Git configuration uses the same
approved identity for future commits; no global identity was changed.

The ten screenshot PNGs were visually reviewed for names, mail, credentials, tokens, local paths,
and unrelated browser content; visible identity is the synthetic `analyst@demo.invalid` and
`Renzai Demo Lab`. The ten screenshots and logo contain no PNG text, EXIF, or timestamp chunks.
Current and history path scans found only deliberate path-detection regexes and synthetic
private-address examples in SSRF tests, not machine-specific owner paths. The actual local
`.env`, generated demo environment, virtualenv, Node modules, cache, and reports are ignored.
A generated `tsconfig.tsbuildinfo` was removed from the candidate index and is now ignored.

The owner subsequently classified the legacy private verifier email literal as private and
authorized a narrow local content-history rewrite. Only the affected tip commit changed; its
parent, message, author and committer identities, timestamps, and all unrelated content were
preserved. The literal-specific verifier branch was removed while the general non-reserved email
detector remained in place. A Codex checkpoint ref that reached the old tree was removed, reflogs
were expired, and unreachable objects were pruned. `main` is the only remaining ref.

Final scans of the current candidate, every reachable commit and ref, the screenshot set, and the
rebuilt release artifacts found neither private identity. The external pre-rewrite recovery
artifacts remain private and must never be published. The history privacy blocker is remediated.
