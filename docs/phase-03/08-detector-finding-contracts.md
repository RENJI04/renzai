# Detector and finding contracts

## Stable identifiers and versions

Detector IDs are lowercase dotted names: `prompt_injection.direct`, `prompt_injection.instruction_override`, `system_prompt.extraction`, `jailbreak.pattern`, `role.manipulation`, `obfuscation.encoded`, `secrets.api_key`, `pii.email`, `pii.phone`, `url.suspicious`, `tool.manipulation_indicator`, `exfiltration.attempt`. The names identify detector families, not implemented algorithms. A detector version uses semantic `major.minor.patch`; the ruleset version identifies the bundle invoked for one analysis. A rule/evidence semantics change increments the relevant version. Results keep detector ID/version and ruleset version so history remains interpretable; deprecation stops new invocation but does not rewrite old findings.

The initial version-controlled regression corpus must include positive, negative, adversarial and privacy cases. False Positive incident status does not automatically change a detector or corpus. Human-reviewed promotion creates a new corpus revision; profile or detector rollout is a separate audited action.

## Canonical finding

| Field | Type/meaning | Constraint |
|---|---|---|
| `finding_id` | UUIDv7 | Unique within analysis; never authorization. |
| `detector_id`, `detector_version`, `ruleset_version` | Stable strings | Must identify published version. |
| `category` | One V1 category enum | Maps to risk-profile base weight. |
| `direction` | `input|output` | Must match analysis phase. |
| `severity` | `low|medium|high|critical` | Detector-local qualitative severity, not final risk band. |
| `confidence` | Integer 0–100 | Evidence confidence, not attack-success probability. |
| `evidence` | Tagged union below | Privacy-filtered for caller/storage mode. |
| `safe_explanation` | Bounded text/code | No raw secret, prompt or provider body. |
| `metadata` | Allowlisted typed map | Safe classification/context only. |
| `overlap_group` | Stable per-analysis opaque group ID/null | Used by risk deduplication; no raw span content. |

`evidence` is one of: `{kind:"redacted_excerpt", text:"…[REDACTED:EMAIL]…"}`, `{kind:"span", start, end, normalization_version}` with half-open normalized-text offsets, or `{kind:"classification_only", label}`. Storage may downgrade excerpt to span/classification under REDACTED/METADATA_ONLY. Span offsets are not a promise that original text is retained. Explanations and metadata must never embed the detected secret value. The result may expose multiple findings sharing an overlap group, but risk counts only the strongest contribution from that group.

The exact V1 category enum is `prompt_injection|instruction_override|system_prompt_extraction|jailbreak|role_manipulation|encoded_obfuscated|secret_exposure|pii_exposure|suspicious_url|tool_manipulation_indicator|data_exfiltration_indicator`, matching the [risk profile](09-risk-scoring-specification.md). Initial detector-to-category mapping, in the ID order above, is respectively `prompt_injection`, `instruction_override`, `system_prompt_extraction`, `jailbreak`, `role_manipulation`, `encoded_obfuscated`, `secret_exposure`, `pii_exposure`, `pii_exposure`, `suspicious_url`, `tool_manipulation_indicator`, `data_exfiltration_indicator`. “Tool manipulation” is textual detection only; V1 does not execute or approve tool calls. Output detectors specifically identify secret and PII leakage. No regex/rule implementation is defined here.
