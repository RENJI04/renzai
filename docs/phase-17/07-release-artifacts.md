# Release artifacts

Generated binaries, archives, SBOMs, and checksums remain outside Git history. Phase 17B may attach
only the sanitized source archive, checksum manifest, and SPDX SBOMs to the GitHub Release.

| Artifact | Local name | Bytes | SHA-256 | Publication |
| --- | --- | ---: | --- | --- |
| Source | `renzai-1.0.0-source.tar.gz` | Recorded in external manifest | Recorded in external manifest | Approved GitHub Release attachment |
| Python SDK wheel | `renzai_sdk-0.1.0-py3-none-any.whl` | 21,227 | `b44697a80840c3ab62401deb2630db7e5db93b40aef010ae13a10f8fc5058f60` | Not approved for PyPI |
| Python SDK sdist | `renzai_sdk-0.1.0.tar.gz` | 20,907 | `5eb4ca19666e919c5b365d7974a3c58b121764c5b8d2c004d8efbad4ce32227f` | Not approved for PyPI |
| TypeScript SDK | `renzai-sdk-0.1.0.tgz` | 27,531 | `a18bc90e97f7371e65d42b9dd65711cdc9c78d82f487340009f27ee8aa0d7373` | Not approved for npm |
| API SBOM | `sbom-release-api.spdx.json` | 1,597,483 | `e480824c034be22a74391206abac58bb2a5813aefd5580baec3d41cf5b11d00b` | Approved GitHub Release attachment |
| Worker SBOM | `sbom-release-worker.spdx.json` | 1,597,924 | `8738911da04de14f239978fd96bd05bcb84aaa8f6579ea12ff6dba612d2bb41c` | Approved GitHub Release attachment |
| Web SBOM | `sbom-release-web.spdx.json` | 267,618 | `4fbc5c433208328b04cd748e2dc80abd5e61a3d8f878aa77bcbd0a8f5180bb5a` | Approved GitHub Release attachment |
| Checksums | `SHA256SUMS` | Generated after the source archive | Self-excluded | Approved GitHub Release attachment |
| Notes and images | [Release notes](../releases/v1.0.0.md) and synthetic screenshots | In source archive | Source archive checksum | Published with repository source |

The image plan is `renzai-api:1.0.0`, `renzai-worker:1.0.0`, and `renzai-web:1.0.0`,
preferably under `ghcr.io/RENJI04/` after separate registry authorization. The `1.0.0-rc`
local tags used for verification are not public. The SBOMs may be attached to the GitHub Release;
container registry publication remains separately authorized and is not part of Phase 17B.

The source and SDK archives were unpacked and checked for private identities, other personal data,
secrets, and machine-specific paths; no release blocker was found. The external checksum manifest
covers the source archive, both SDK formats, and the three final SBOMs. It intentionally excludes
itself. The pre-remediation source archive is quarantined outside this artifact set and must never
be published.
