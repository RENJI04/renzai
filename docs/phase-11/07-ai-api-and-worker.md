# AI API and worker

Configuration endpoints live under `/api/v1/organizations/{org}/ai-providers`; they provide create, list, masked get/update, enable/disable, and connection validation.

`POST /api/v1/organizations/{org}/incidents/{incident}/ai-analysis` accepts only `task_type` and a bounded disclosure mode, commits a real `pending` request, and returns `202`. `GET` on the incident path lists results; `GET /api/v1/organizations/{org}/ai-analysis/{request}` reads one result. Arbitrary prompt text is not accepted.

Celery accepts JSON only. `renzai.ai_intelligence.process` receives tenant/request UUID strings, performs zero automatic retries, and is idempotent under duplicate delivery. No raw incident content or credential enters the broker message. Queue dispatch failure is persisted as `failed/queue_unavailable`.
