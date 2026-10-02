# AI task contracts

The bounded task enum is:

- `incident_summary`: `summary`, up to ten `key_points`.
- `attack_explanation`: `interpretation`, observed techniques, and textual uncertainty.
- `mitigation_suggestion`: up to ten title/rationale/priority recommendations.
- `policy_suggestion`: rationale plus a proposed policy draft.

Each task has an immutable `*-v1` prompt-template identifier. Provider output must be JSON, remain below 64 KiB, reject extra fields, and satisfy task-specific string/array/enum bounds. Results are rendered as plain React text, never HTML. Token counts are stored when supplied; monetary cost is not inferred.
