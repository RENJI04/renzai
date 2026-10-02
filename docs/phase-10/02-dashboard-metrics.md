# Dashboard metrics

| Metric | Definition |
|---|---|
| Analyses | `AnalysisResult.status = completed`, joined to an in-window `SecurityEvent` |
| Gateway requests | Durable `GatewayProviderCall` rows; one input/output pair remains one request |
| Threats detected | Completed analyses whose final `finding_count > 0` |
| Threat rate | Threat-bearing completed analyses / completed analyses; numerator and denominator are returned |
| Blocked/review/redacted | Completed analyses by final policy action |
| Critical | Completed analyses by final risk severity, not detector-local severity |
| Open incidents | In-window incidents whose current status is open |

Finding categories and detector metrics expose both finding count and distinct affected analyses. Thus two same-category findings in one analysis count as two findings and one affected analysis. Risk and policy distributions include zero-valued enum members. Top categories/detectors, applications, and environments are capped at 10; provider rows are capped at 20 with deterministic count-descending, identifier/name tie-break ordering.

Provider outcomes are reported only where stored: completed, provider timeout/error, configuration error, output block/review/inspection failure, plus honest average integer-millisecond latency. Input inspection failures are not inferred from absent provider-call rows.
