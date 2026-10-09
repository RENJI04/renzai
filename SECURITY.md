# Security policy

Renzai v1.0.0 is a release candidate until publication is explicitly approved. The policy below
describes maintenance after that publication; it is not a promise of a production SLA.

| Version | Security fixes |
| --- | --- |
| Latest published 1.0.x | Supported after publication |
| Earlier 1.0.x | Upgrade to the latest patch release |
| Unpublished development commits and pre-1.0 history | Not supported releases |

Security fixes target the latest supported patch version. A fix may require an upgrade or
configuration change. No older major/minor line is promised support, and a self-hosted operator
remains responsible for deployment, secrets, TLS, backups, monitoring, and timely upgrades.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting on the Renzai repository once it is available. If that
private channel has not yet been enabled, contact the maintainers through a private channel listed
on the repository profile and request a secure reporting route **without including exploit details**.
Do not open a public issue containing a vulnerability, token, personal data, or instructions that
put users at immediate risk. No personal maintainer email is designated as a reporting address.

Include the affected commit/version, component, prerequisites, impact, minimal reproduction, relevant
logs with secrets removed, and any suggested mitigation. A proof of concept is helpful but should be
bounded to synthetic data and must not target systems you do not own or have permission to test.

Maintainers should acknowledge a complete private report, validate it, coordinate a remediation and
disclosure timeline, and credit the reporter if requested. Please allow a reasonable remediation
window before public disclosure. This policy does not authorize testing against third-party services,
data access, persistence, denial of service, social engineering, or privacy violations.
