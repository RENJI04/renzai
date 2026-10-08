# Security policy

Renzai is approaching its first public release. Before v1.0, security fixes target the current `main`
branch. A supported-version table and release service policy will be finalized in Phase 17; no older
pre-release commit should be assumed supported.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature when it is enabled for the repository.
If private reporting is unavailable, contact the maintainers through a private channel listed on the
repository profile and ask for a secure reporting route without including exploit details. Do not
open a public issue containing a vulnerability, token, personal data, or instructions that put users
at immediate risk.

Include the affected commit/version, component, prerequisites, impact, minimal reproduction, relevant
logs with secrets removed, and any suggested mitigation. A proof of concept is helpful but should be
bounded to synthetic data and must not target systems you do not own or have permission to test.

Maintainers should acknowledge a complete private report, validate it, coordinate a remediation and
disclosure timeline, and credit the reporter if requested. Please allow a reasonable remediation
window before public disclosure. This policy does not authorize testing against third-party services,
data access, persistence, denial of service, social engineering, or privacy violations.
