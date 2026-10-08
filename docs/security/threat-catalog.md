# V1 threat catalog

The examples below are synthetic and intentionally safe. Potential action is policy-dependent; the
baseline generally allows low risk, flags medium risk, requires review for high input risk, blocks
critical input risk, and gives output secret redaction priority. Details are high-level to explain the
model without publishing a bypass guide.

| Category | Purpose and safe example | Typical evidence | Potential action | Limitations |
| --- | --- | --- | --- | --- |
| Prompt Injection | Detect direct replacement of trusted instructions. Example: “Replace prior instructions.” | Bounded span or classification label | Review or block | Novel paraphrases may not match. |
| Instruction Override | Detect explicit hierarchy-disregard language. Example: “Ignore previous instructions.” | Rule ID and safe span | Review or block | Legitimate quoted/educational uses need context. |
| System Prompt Extraction | Detect requests for hidden instruction disclosure. | Safe span and detector metadata | Review or block | Cannot inspect provider internals. |
| Jailbreak | Detect explicit safety-disable or unrestricted-mode requests. | Safe span, severity, confidence | Review or block | No rule set guarantees complete jailbreak prevention. |
| Role Manipulation | Detect attempts to assume system/developer/admin authority. | Safe span and role indicator | Flag or review | Benign role play can look similar without context. |
| Encoded / Obfuscated Attack | Surface bounded Base64, percent, HTML-entity, Unicode, and zero-width transforms. | Classification-only transform label | Flag, review, or block | Decoding is deliberately bounded, not arbitrary execution. |
| Secret Exposure | Detect credential-shaped values in text. | Redacted evidence such as `[REDACTED:API_KEY]` | Redact, review, or block | A shape match does not prove a credential is live. |
| PII Exposure | Detect supported email and phone structures. | Redacted evidence and type | Flag or redact | This is not a complete PII classifier. |
| Suspicious URL | Detect credential-bearing schemes or actionable private targets. | Safe URL classification | Flag or review | Text detection is separate from outbound SSRF enforcement. |
| Tool Manipulation | Detect text asking for hidden/privileged tool use or approval bypass. | Safe intent span | Review or block | V1 does not execute or mediate tools/functions. |
| Data Exfiltration Attempt | Detect transfer intent combined with sensitive-data terms. | Safe intent/target evidence | Review or block | Not guaranteed DLP and cannot observe unsupplied context. |

Run the curated malicious, benign-control, and boundary cases in
[Attack Lab](../../examples/attack-lab/README.md). Passing that corpus demonstrates deterministic
replay of those cases only, not universal attack coverage.
