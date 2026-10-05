# Logging and correlation

Production defaults use structured JSON logs with UTC timestamp, level, service, environment, bounded request ID, route template, status, and duration. Existing redaction removes fields whose names indicate authorization, cookies, credentials, keys, passwords, prompts, responses, sessions, tokens, or content, including nested structures.

Nginx accepts only request IDs matching a bounded visible character pattern; otherwise it creates its own ID. The API validates again, returns the ID, and places it in structured log context. Celery dispatch adds that ID to message headers while task arguments remain identifier-only. Worker hooks bind the correlation ID for safe task lifecycle logs.

Prompt text, AI output, incident evidence, raw PII, cookies, authorization headers, and secret material must not be added to logs. Correlation IDs aid investigation but are not authentication or authorization tokens.
