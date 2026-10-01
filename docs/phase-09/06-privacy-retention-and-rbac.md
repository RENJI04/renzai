# Privacy, retention, and RBAC

Automatic incident titles and summaries are deterministic safe metadata. They contain classification, action, direction, source, and score, not raw prompt, response, or credentials. Manual title and summary text is bounded, normalized, and passed through the deterministic sensitive-data redactor before persistence. This is a backstop for recognized patterns, not a guarantee that arbitrary operator-entered secrets can be identified; operators should enter safe metadata only. Detail reuses stored privacy-filtered `SecurityEvent.content` and `Finding.evidence`:

- `FULL`: returns stored content where the application contract retained it.
- `REDACTED`: returns only the stored redacted representation; the original is never reconstructed.
- `METADATA_ONLY`: omits content and reports `not_retained`.
- Expired linked evidence: returns `content_no_longer_retained` while incident metadata, timeline, and comments remain usable.

Every query includes organization scope and critical ancestry is also database-enforced. Foreign IDs return `not_found_or_hidden`.

| Capability | Owner | Admin | Security Analyst | Developer | Viewer |
|---|---:|---:|---:|---:|---:|
| List/detail | Yes | Yes | Yes | Yes | Yes |
| Status/false positive | Yes | Yes | Yes | No | No |
| Assign/unassign | Yes | Yes | Yes | No | No |
| Comment | Yes | Yes | Yes | Yes | No |
| Manual create | Yes | Yes | Yes | No | No |
