# License and versioning

The owner explicitly selected Apache License 2.0 for the repository. The canonical text is in
[`LICENSE`](../../LICENSE); local SDK package archives must carry the same license. Apache-2.0
permits commercial and proprietary reuse, requires preservation of license and notices and
prominent modification notices, and provides an express contributor patent grant subject to its
terms. The shorter MIT license also permits broad reuse with copyright/license notice retention
but does not state a comparable express patent grant. Neither is a copyleft license. Apache-2.0
was selected for the explicit patent treatment and notice clarity expected of a security platform.
Contributors remain responsible for having rights to their contributions; a separate CLA is not
created by this decision.

The application, root Python distribution, private web package, and OpenAPI application metadata
are `1.0.0` in the release candidate. API protocol and detector/risk schema versions are separate
contract numbers, not publication claims. The two local SDK packages retain their independently
versioned `0.1.0` metadata and remain unpublished. A future PyPI/npm publication requires account,
namespace, provenance, and credential decisions; the application release does not imply those
packages exist on public registries.
