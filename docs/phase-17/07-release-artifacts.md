# Release artifacts

Generated binaries, archives, SBOMs, and checksums remain outside Git history. Phase 17B may attach
only the sanitized source archive, checksum manifest, and SPDX SBOMs to the GitHub Release.

| Artifact | Local name | Bytes | SHA-256 | Publication |
| --- | --- | ---: | --- | --- |
| Source | `renzai-1.0.0-source.tar.gz` | Recorded in external manifest | Recorded in external manifest | Approved GitHub Release attachment |
| Python SDK wheel | `renzai_sdk-0.1.0-py3-none-any.whl` | 21,227 | `b44697a80840c3ab62401deb2630db7e5db93b40aef010ae13a10f8fc5058f60` | Not approved for PyPI |
| Python SDK sdist | `renzai_sdk-0.1.0.tar.gz` | 20,907 | `5eb4ca19666e919c5b365d7974a3c58b121764c5b8d2c004d8efbad4ce32227f` | Not approved for PyPI |
| TypeScript SDK | `renzai-sdk-0.1.0.tgz` | 27,531 | `a18bc90e97f7371e65d42b9dd65711cdc9c78d82f487340009f27ee8aa0d7373` | Not approved for npm |
| API SBOM | `sbom-release-api.spdx.json` | 1,251,025 | `93f71a51a4f8bc48b94bf6988b4c3c7965a5e46865200f51f1108396c1d14051` | Approved GitHub Release attachment |
| Worker SBOM | `sbom-release-worker.spdx.json` | 1,251,358 | `d1d9b5371ec1fa6ad2f6440a989aa33b47260ad7968fb20fbe14e14064c3eca2` | Approved GitHub Release attachment |
| Web SBOM | `sbom-release-web.spdx.json` | 269,173 | `d86b6146784bf1402a622b8eb781b58a28368ffa9ed87b7b20201c64b3cd9223` | Approved GitHub Release attachment |
| Checksums | `SHA256SUMS` | Generated after the source archive | Self-excluded | Approved GitHub Release attachment |
| Notes and images | [Release notes](../releases/v1.0.0.md) and synthetic screenshots | In source archive | Source archive checksum | Published with repository source |

The image plan is `renzai-api:1.0.0`, `renzai-worker:1.0.0`, and `renzai-web:1.0.0`,
preferably under `ghcr.io/RENJI04/` after separate registry authorization. The `1.0.0-rc`
local tags used for verification are not public. The SBOMs may be attached to the GitHub Release;
container registry publication remains separately authorized and is not part of Phase 17B.

The source and SDK archives were unpacked and checked for private identities, other personal data,
secrets, and machine-specific paths; no release blocker was found. The public checksum manifest
covers the final source archive and three final SBOMs; unpublished SDK packages remain local and
are not included in the public artifact set. The manifest intentionally excludes itself. The
pre-remediation source archive is quarantined outside this artifact set and must never be published.
