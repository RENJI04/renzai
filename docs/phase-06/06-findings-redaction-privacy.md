# Findings, redaction, and privacy

Finding evidence is the Phase 3 union: normalized `span`, `redacted_excerpt`, or `classification_only`. Secrets and PII use `[REDACTED:API_KEY]`, `[REDACTED:SECRET]`, `[REDACTED:EMAIL]`, and `[REDACTED:PHONE]`. Explanations and metadata contain only rule/transform classification, never matched secret values. Overlap groups are stable hashes of detector/span identity; exact duplicate evidence is suppressed deterministically without removing detector identity.

Persistence behavior is selected from the application snapshot at event time:

- `FULL`: stores bounded original content for qualifying events only after an Owner/Admin explicitly selects it.
- `REDACTED`: stores typed-placeholder content for non-safe events.
- `METADATA_ONLY`: stores no content and downgrades stored evidence to classification only.
- Any mode with zero findings and safe-content persistence off stores no content.

One transaction writes the SecurityEvent, AnalysisResult, and all Findings. Commit failure is propagated, so no response claims durable event creation. Each row records normalization/ruleset/detector versions and the event’s privacy/retention snapshot. Audit events contain only safe resource metadata, never API keys or analyzed content.
