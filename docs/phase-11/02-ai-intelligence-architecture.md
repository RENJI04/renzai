# AI intelligence architecture

The `ai_intelligence` module owns configuration, request, context, output-validation, and result records. API writes commit a `pending` request before dispatching only `organization_id` and `request_id` to Celery. The worker re-fetches tenant-scoped state, atomically claims `pending → running`, builds privacy-approved context, calls the dedicated provider abstraction, validates output, and atomically commits a result with `completed`. Duplicate worker delivery observes the existing state and does not call the provider again.

Provider or output failure changes only the AI request to `failed` with a safe error code. Incident, analysis, findings, risk, policy decisions, and Gateway outcomes are never mutated. There is no AI call in `/api/v1/analyze` or `/v1/chat/completions`.
