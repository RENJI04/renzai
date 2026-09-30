# V1 deterministic detectors

Ruleset `1.0.0` registers these stable detectors in order:

| Detector ID | Category | Principal signals |
|---|---|---|
| `prompt_injection.direct` | prompt_injection | explicit replacement and smuggled authority markers |
| `prompt_injection.instruction_override` | instruction_override | ignore/disregard/override/highest-priority phrases |
| `system_prompt.extraction` | system_prompt_extraction | hidden system/developer instruction disclosure requests |
| `jailbreak.pattern` | jailbreak | safety disabling and unrestricted mode requests |
| `role.manipulation` | role_manipulation | privileged impersonation or role switching |
| `obfuscation.encoded` | encoded_obfuscated | Base64, percent, entity, Unicode escape, or zero-width indicators |
| `secrets.api_key` | secret_exposure | Renzai/common keys, bearer values, PEM headers, credential URLs |
| `pii.email` | pii_exposure | email structures, excluding reserved documentation domains |
| `pii.phone` | pii_exposure | bounded international/common phone structures |
| `url.suspicious` | suspicious_url | credential URLs, sensitive schemes, actionable private targets |
| `tool.manipulation_indicator` | tool_manipulation_indicator | hidden/privileged invocation and approval bypass text |
| `exfiltration.attempt` | data_exfiltration_indicator | extraction intent combined with sensitive targets |

Attack-language rules suppress explicit training/documentation context where practical. Patterns are individually explainable, bounded by the endpoint input ceiling, and contain no catastrophic nested quantifiers. V1 is a transparent indicator set, not universal detection; multilingual/homoglyph breadth, semantic paraphrase, and novel evasion remain known limitations.
