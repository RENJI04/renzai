# Detector framework

The framework-independent domain lives under `renzai.modules.security.domain` and imports no FastAPI, SQLAlchemy, Redis, Celery, or HTTP client. `DetectorInput` carries normalized content, direction, safe context, and normalization version. `DetectorFinding` carries stable detector/ruleset versions, category, detector-local severity, evidence confidence, privacy-safe evidence, bounded explanation, allowlisted metadata, and optional overlap group.

The registry is a fixed tuple with stable execution order. Detector version and active ruleset are both `1.0.0`. Detectors are pure and may not persist, call networks/providers, mutate peers, score final risk, or decide policy. A required detector exception raises `InspectionFailure`; the orchestration layer never translates it to an empty successful finding list.

Confidence is deterministic evidence confidence from 0–100, not probability of attack success. Detector-local `low|medium|high|critical` severity describes that rule match only; it is not the Phase 7 final risk band.
