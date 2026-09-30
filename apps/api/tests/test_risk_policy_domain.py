from __future__ import annotations

from uuid import uuid4

import pytest

from renzai.modules.policies.domain import (
    PolicyAction,
    PolicyCondition,
    PolicyFacts,
    PolicySnapshot,
    PolicyValidationError,
    evaluate_policies,
)
from renzai.modules.risk.domain import RiskFinding, evaluate_risk, renzai_v1_profile
from renzai.modules.security.domain.types import Category, Direction


def risk_finding(
    category: Category,
    confidence: int,
    *,
    detector_id: str | None = None,
    start: int | None = 0,
    end: int | None = 8,
    overlap_group: str | None = None,
    direction: Direction = Direction.INPUT,
) -> RiskFinding:
    return RiskFinding(
        finding_id=str(uuid4()),
        category=category,
        detector_id=detector_id or f"test.{category.value}",
        detector_version="1.0.0",
        confidence=confidence,
        direction=direction,
        normalized_start=start,
        normalized_end=end,
        overlap_group=overlap_group,
    )


@pytest.mark.parametrize(
    ("findings", "score", "severity", "confidence"),
    [
        ([], 0, "low", 0),
        ([risk_finding(Category.SUSPICIOUS_URL, 40)], 8, "low", 40),
        ([risk_finding(Category.PROMPT_INJECTION, 95)], 52, "high", 95),
        ([risk_finding(Category.ENCODED_OBFUSCATED, 90)], 32, "medium", 90),
        (
            [
                risk_finding(
                    Category.SECRET_EXPOSURE,
                    95,
                    detector_id="secrets.api_key",
                    direction=Direction.OUTPUT,
                )
            ],
            80,
            "critical",
            95,
        ),
    ],
)
def test_phase3_worked_risk_vectors(
    findings: list[RiskFinding], score: int, severity: str, confidence: int
) -> None:
    result = evaluate_risk(findings, renzai_v1_profile())
    assert (result.risk_score, result.severity.value, result.confidence) == (
        score,
        severity,
        confidence,
    )


def test_corroboration_overlap_caps_rounding_and_no_third_addition() -> None:
    independent = [
        risk_finding(Category.PROMPT_INJECTION, 95, start=0, end=8),
        risk_finding(Category.SYSTEM_PROMPT_EXTRACTION, 90, start=20, end=28),
        risk_finding(Category.DATA_EXFILTRATION_INDICATOR, 100, start=40, end=48),
    ]
    result = evaluate_risk(independent, renzai_v1_profile())
    assert result.risk_score == 85  # highest 60 + capped bonus 25; third adds nothing
    assert result.corroboration_bonus == 25

    overlap = [
        risk_finding(Category.PROMPT_INJECTION, 95, overlap_group="same", start=0, end=20),
        risk_finding(
            Category.SYSTEM_PROMPT_EXTRACTION,
            90,
            overlap_group="same",
            start=4,
            end=18,
        ),
    ]
    overlapped = evaluate_risk(overlap, renzai_v1_profile())
    assert overlapped.risk_score == 52
    assert sum(item.retained for item in overlapped.contributions) == 1

    same_category = [
        risk_finding(Category.PROMPT_INJECTION, 95, start=0, end=8),
        risk_finding(Category.PROMPT_INJECTION, 90, start=20, end=28),
    ]
    assert evaluate_risk(same_category, renzai_v1_profile()).corroboration_bonus == 0

    rounding = risk_finding(Category.SUSPICIOUS_URL, 43)
    assert evaluate_risk([rounding], renzai_v1_profile()).risk_score == 9

    capped = [
        risk_finding(Category.SECRET_EXPOSURE, 100, direction=Direction.INPUT),
        risk_finding(Category.DATA_EXFILTRATION_INDICATOR, 100, start=20, end=28),
    ]
    assert evaluate_risk(capped, renzai_v1_profile()).risk_score == 100


def condition(field: str, operator: str, value: object) -> PolicyCondition:
    return PolicyCondition(field=field, operator=operator, value=value)


def snapshot(
    scope_kind: str,
    scope_id: str,
    action: PolicyAction,
    *,
    priority: int = 10,
    conditions: tuple[PolicyCondition, ...] = (condition("risk_score", "greater_or_equal", 0),),
) -> PolicySnapshot:
    return PolicySnapshot(
        policy_id=str(uuid4()),
        version_id=str(uuid4()),
        version=1,
        scope_kind=scope_kind,
        scope_id=scope_id,
        phase="input",
        priority=priority,
        enabled=True,
        action=action,
        rationale_code=f"test_{action.value}",
        condition_mode="all",
        conditions=conditions,
        redaction_targets=("pii_exposure",) if action is PolicyAction.REDACT else (),
    )


def facts(org: str, app: str, env: str) -> PolicyFacts:
    return PolicyFacts(
        phase="input",
        categories=frozenset({"prompt_injection"}),
        detector_ids=frozenset({"prompt_injection.direct"}),
        risk_score=52,
        severity="high",
        confidence_band="critical",
        application_id=app,
        environment_type="production",
        source="analyze",
        organization_id=org,
        environment_id=env,
    )


@pytest.mark.parametrize(
    ("field", "operator", "value"),
    [
        ("phase", "equals", "input"),
        ("category_set", "contains_category", "prompt_injection"),
        ("detector_id_set", "in", ["prompt_injection.direct"]),
        ("risk_score", "greater_or_equal", 50),
        ("risk_score", "less_or_equal", 60),
        ("severity", "in", ["high", "critical"]),
        ("confidence_band", "equals", "critical"),
        ("application_id", "equals", "00000000-0000-0000-0000-000000000001"),
        ("environment_type", "equals", "production"),
        ("source", "equals", "analyze"),
    ],
)
def test_bounded_condition_grammar_accepts_each_fact_and_operator(
    field: str, operator: str, value: object
) -> None:
    assert condition(field, operator, value)


@pytest.mark.parametrize(
    ("field", "operator", "value"),
    [
        ("risk_score", "regex", ".*"),
        ("unknown", "equals", "x"),
        ("severity", "greater_or_equal", "high"),
        ("phase", "equals", "sideways"),
        ("risk_score", "greater_or_equal", 101),
        ("detector_id_set", "in", []),
    ],
)
def test_bounded_condition_grammar_rejects_invalid_shapes(
    field: str, operator: str, value: object
) -> None:
    with pytest.raises(PolicyValidationError):
        condition(field, operator, value)


def test_policy_precedence_and_no_match_are_exact() -> None:
    org, app, env = (str(uuid4()) for _ in range(3))
    current = facts(org, app, env)
    decision = evaluate_policies(
        [
            snapshot("organization", org, PolicyAction.BLOCK),
            snapshot("application", app, PolicyAction.ALLOW),
        ],
        current,
    )
    assert decision.action is PolicyAction.BLOCK
    assert decision.selected_policy_id == decision.scope_winners[0].policy_id

    same_action = evaluate_policies(
        [
            snapshot("organization", org, PolicyAction.FLAG),
            snapshot("application", app, PolicyAction.FLAG),
            snapshot("environment", env, PolicyAction.FLAG),
        ],
        current,
    )
    assert same_action.selected_scope == "environment"

    no_match = evaluate_policies(
        [
            snapshot(
                "organization",
                org,
                PolicyAction.BLOCK,
                conditions=(condition("risk_score", "greater_or_equal", 90),),
            )
        ],
        current,
    )
    assert no_match.action is PolicyAction.ALLOW
    assert no_match.selected_policy_id is None
    assert no_match.scope_winners == ()
    assert no_match.rationale_code == "no_policy_matched"


@pytest.mark.parametrize(
    ("organization_action", "application_action", "environment_action", "expected"),
    [
        (PolicyAction.BLOCK, None, PolicyAction.ALLOW, PolicyAction.BLOCK),
        (PolicyAction.FLAG, PolicyAction.BLOCK, None, PolicyAction.BLOCK),
        (PolicyAction.ALLOW, None, PolicyAction.REDACT, PolicyAction.REDACT),
        (None, PolicyAction.REQUIRE_REVIEW, PolicyAction.FLAG, PolicyAction.REQUIRE_REVIEW),
        (PolicyAction.FLAG, PolicyAction.FLAG, PolicyAction.FLAG, PolicyAction.FLAG),
    ],
)
def test_cross_scope_safety_rank_matrix(
    organization_action: PolicyAction | None,
    application_action: PolicyAction | None,
    environment_action: PolicyAction | None,
    expected: PolicyAction,
) -> None:
    org, app, env = (str(uuid4()) for _ in range(3))
    policies = [
        snapshot(scope, scope_id, action)
        for scope, scope_id, action in (
            ("organization", org, organization_action),
            ("application", app, application_action),
            ("environment", env, environment_action),
        )
        if action is not None
    ]
    decision = evaluate_policies(policies, facts(org, app, env))
    assert decision.action is expected
    if organization_action == application_action == environment_action == PolicyAction.FLAG:
        assert decision.selected_scope == "environment"


@pytest.mark.parametrize(
    ("field", "operator", "value"),
    [
        ("category_set", "equals", "prompt_injection"),
        ("risk_score", "equals", True),
        ("risk_score", "in", [0] * 21),
        ("environment_type", "equals", "preview"),
        ("source", "equals", "unknown"),
        ("application_id", "equals", "not-a-uuid"),
        ("severity", "equals", {"script": "deny"}),
        ("severity", "in", [["high"]]),
    ],
)
def test_condition_grammar_rejects_malformed_values(
    field: str, operator: str, value: object
) -> None:
    with pytest.raises(PolicyValidationError):
        condition(field, operator, value)
