from __future__ import annotations

from typing import Any


def analyze_payload() -> dict[str, Any]:
    return {
        "analysis_id": "01900000-0000-7000-8000-000000000001",
        "event_id": "01900000-0000-7000-8000-000000000002",
        "timestamp": "2026-10-03T00:00:00+00:00",
        "direction": "input",
        "source": "analyze",
        "safe": False,
        "no_detected_threat": False,
        "action": "flag",
        "risk_score": 43,
        "severity": "medium",
        "confidence": 90,
        "risk_profile": {"id": "profile", "name": "renzai-v1", "version": 1},
        "normalization_version": "1.0.0",
        "detector_ruleset_version": "1.0.0",
        "findings": [
            {
                "finding_id": "01900000-0000-7000-8000-000000000003",
                "detector_id": "prompt-injection",
                "detector_version": "1.0.0",
                "ruleset_version": "1.0.0",
                "category": "prompt_injection",
                "direction": "input",
                "severity": "medium",
                "confidence": 90,
                "evidence": {"kind": "pattern", "label": "synthetic"},
                "safe_explanation": "Synthetic prompt-injection indicator.",
                "metadata": {},
            }
        ],
        "risk_contributions": [],
        "risk_explanation": {"base_score": 43},
        "policy_decision": {
            "policy_decision_id": "01900000-0000-7000-8000-000000000004",
            "policy_match": None,
            "evaluated_policy_versions": [],
            "scope_winners": [],
            "rationale_code": "no_policy_matched",
            "redaction_targets": [],
        },
        "timing": {"total_ms": 2},
        "correlation_id": "corr-safe",
        "future_additive_field": True,
    }


def incident_payload(identifier: str = "incident-1") -> dict[str, Any]:
    return {
        "incident_id": identifier,
        "organization_id": "org-1",
        "application_id": None,
        "environment_id": None,
        "status": "open",
        "severity": "high",
        "source": "manual",
        "title": "Synthetic incident",
        "safe_summary": "Safe synthetic summary.",
        "version": 1,
        "created_at": "2026-10-03T00:00:00+00:00",
        "updated_at": "2026-10-03T00:00:00+00:00",
        "assignee_user_id": None,
        "action": None,
        "risk_score": None,
        "category": None,
        "resolved_at": None,
    }


def ai_payload() -> dict[str, Any]:
    return {
        "request_id": "ai-request-1",
        "incident_id": "incident-1",
        "task_type": "incident_summary",
        "status": "pending",
        "ai_generated": True,
        "context_mode": "redacted",
        "incident_version": 1,
        "provider_id": "provider-1",
        "provider_name": "Synthetic provider",
        "model": "synthetic-model",
        "prompt_template_version": None,
        "input_context_version": "1.0.0",
        "output_schema_version": "1.0.0",
        "content": None,
        "usage": None,
        "error_code": None,
        "created_at": "2026-10-03T00:00:00+00:00",
        "completed_at": None,
    }
