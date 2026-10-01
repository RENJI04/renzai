# Phase 9 scope

Phase 9 implements Renzai V1 Incident Management on the Phase 8 baseline. It adds durable tenant-scoped incidents, manual and Gateway creation, lifecycle transitions, assignment, comments, an operator timeline, list/detail APIs, and the Incident Queue UI.

Existing `SecurityEvent`, `AnalysisResult`, `Finding`, `RiskContribution`, `PolicyDecision`, and `GatewayProviderCall` rows remain authoritative. Incidents retain only indexed immutable summary fields and references; they do not copy prompts, provider output, credentials, or finding JSON.

This phase does not implement notifications, webhooks, reviewer approval, AI summaries, mitigation suggestions, analytics, SDKs, ticketing, detector learning, retraining, or policy tuning. Phase 10 has not started.
