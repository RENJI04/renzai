# Deterministic V1 risk-scoring specification

Initial immutable profile: `renzai-v1` version `1`. This is a proposed release baseline to validate with a version-controlled regression corpus before implementation rollout. It is deterministic and does not learn from traffic or false-positive clicks.

## Inputs, weights and arithmetic

| Category | Base weight |
|---|---:|
| prompt_injection | 55 |
| instruction_override | 45 |
| system_prompt_extraction | 55 |
| jailbreak | 50 |
| role_manipulation | 40 |
| encoded_obfuscated | 35 |
| secret_exposure | 80 |
| pii_exposure | 55 |
| suspicious_url | 20 |
| tool_manipulation_indicator | 45 |
| data_exfiltration_indicator | 60 |

For each finding, `raw_i = floor((base_weight(category) × confidence_i + 50) / 100)` (integer half-up rounding). The finding contribution records base, confidence, raw and detector ID. Collapse findings with overlapping normalized evidence spans into one `overlap_group`; retain only the maximum raw contribution per group and list suppressed duplicates. Findings with no usable span are conservatively grouped with other spanless findings from the same source segment, so they cannot manufacture corroboration. A corroboration bonus applies only when the two highest retained groups have **different categories and non-overlapping evidence**: `bonus = min(25, floor(second_highest_raw / 2))`. Otherwise bonus is 0. Base score is `min(100, highest_raw + bonus)`; no third or subsequent finding adds to the score. This cap prevents additive inflation.

Critical floor: for an **output** `secret_exposure` finding with detector `secrets.api_key` at confidence ≥90, score is at least 80. The floor is separately listed in contributions. Final `risk_score = min(100, max(base_score, critical_floor_if_any))`. Analysis confidence is the confidence of the highest retained raw contribution (0 with no findings). These numbers are deliberately explicit so the first regression corpus can challenge them; changing any value/combination rule requires a new immutable profile version and audited rollout.

| Score | Severity |
|---|---|
| 0–24 | low |
| 25–49 | medium |
| 50–74 | high |
| 75–100 | critical |

## Worked specification vectors

| Case | Findings (base × confidence) | Dedup/bonus/floor | Score, severity, confidence |
|---|---|---|---|
| Harmless prompt | None | Highest 0, bonus 0 | **0, low, 0** |
| Weak suspicious phrase/URL | suspicious_url 20 × 40% = 8 | Single group | **8, low, 40** |
| Obvious prompt injection | prompt_injection 55 × 95% = 52 | Single group | **52, high, 95** |
| Output API-key leakage | secret_exposure 80 × 95% = 76 | Critical floor 80 | **80, critical, 95** |
| Injection plus extraction in separate spans | prompt_injection 55 × 95% = 52; system_prompt_extraction 55 × 90% = 50 | Independent categories, bonus min(25,25)=25 | **77, critical, 95** |
| Encoded attack indicator | encoded_obfuscated 35 × 90% = 32 | Single group | **32, medium, 90** |

If injection and extraction overlap the same evidence span, only the stronger 52 contributes and the result is **52, high**. A no-policy-match decision remains `allow` even for a high score; risk and policy action are distinct facts (P3-001). A detector-local severity does not directly set the final band. Confidence is not a calibrated probability of safety or attack success.

## Versioning and compatibility

Each result stores profile ID/version, detector/ruleset versions and contribution/floor details; historical results are never recomputed in place under a newer profile. New versions are reviewed against positive/negative corpus cases, including overlap and critical-floor vectors, then explicitly activated per scope. Rollback selects an older immutable profile. The profile does not call an LLM. Calibration proposals and corpus promotion are human-reviewed and version controlled.
