# Provider and incident analytics

Provider usage is grouped by tenant-qualified provider configuration and configured model. It exposes provider ID/name, model, request count, stored outcome counts, and average persisted latency. No URL, credential field, ciphertext, key identifier, request, or response content is selected or serialized.

Incident analytics return separate counts for open, investigating, resolved, ignored, and false-positive states, plus critical-open and unassigned-open counts. Recent incidents are capped at five and expose only ID, status, severity, category, action, scope IDs, and creation time. Titles, summaries, comments, timeline content, and retained evidence are deliberately absent.

The dashboard links to the Phase 9 Incident Queue instead of duplicating its triage flow. Phase 10 does not introduce MTTR/SLA claims or modify incident lifecycle semantics.
