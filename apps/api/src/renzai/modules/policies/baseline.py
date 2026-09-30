"""Reviewed, explicit V1 application baseline policies."""

from __future__ import annotations

from dataclasses import dataclass

from renzai.modules.policies.domain import PolicyAction, PolicyCondition


@dataclass(frozen=True, slots=True)
class BaselinePolicy:
    key: str
    name: str
    phase: str
    priority: int
    action: PolicyAction
    rationale_code: str
    conditions: tuple[PolicyCondition, ...]
    redaction_targets: tuple[str, ...] = ()


def _severity(phase: str, severity: str, priority: int, action: PolicyAction) -> BaselinePolicy:
    return BaselinePolicy(
        key=f"v1.{phase}.{severity}",
        name=f"V1 {phase.title()} {severity.title()}",
        phase=phase,
        priority=priority,
        action=action,
        rationale_code=f"baseline_{phase}_{severity}_{action.value}",
        conditions=(PolicyCondition("severity", "equals", severity),),
    )


BASELINE_POLICIES = (
    _severity("input", "critical", 100, PolicyAction.BLOCK),
    _severity("input", "high", 200, PolicyAction.REQUIRE_REVIEW),
    _severity("input", "medium", 300, PolicyAction.FLAG),
    _severity("input", "low", 400, PolicyAction.ALLOW),
    BaselinePolicy(
        key="v1.output.secret_exposure",
        name="V1 Output Secret Redaction",
        phase="output",
        priority=50,
        action=PolicyAction.REDACT,
        rationale_code="baseline_output_secret_redact",
        conditions=(PolicyCondition("category_set", "contains_category", "secret_exposure"),),
        redaction_targets=("secret_exposure",),
    ),
    _severity("output", "critical", 100, PolicyAction.BLOCK),
    _severity("output", "high", 200, PolicyAction.REQUIRE_REVIEW),
    _severity("output", "medium", 300, PolicyAction.FLAG),
    _severity("output", "low", 400, PolicyAction.ALLOW),
)
