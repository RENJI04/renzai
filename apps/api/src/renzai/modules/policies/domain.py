"""Framework-independent bounded policy grammar and deterministic evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from renzai.modules.security.domain.types import Category, Severity

MAX_CONDITIONS = 20
MAX_LIST_VALUES = 20
DETECTOR_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")


class PolicyValidationError(ValueError):
    pass


class PolicyEvaluationError(RuntimeError):
    pass


class PolicyAction(StrEnum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    REDACT = "redact"
    REQUIRE_REVIEW = "require_review"


ACTION_RANK = {
    PolicyAction.ALLOW: 1,
    PolicyAction.FLAG: 2,
    PolicyAction.REDACT: 3,
    PolicyAction.REQUIRE_REVIEW: 4,
    PolicyAction.BLOCK: 5,
}
SCOPE_RANK = {"organization": 1, "application": 2, "environment": 3}
ALLOWED_FIELDS = {
    "phase",
    "category_set",
    "detector_id_set",
    "risk_score",
    "severity",
    "confidence_band",
    "application_id",
    "environment_type",
    "source",
}
FIELD_OPERATORS = {
    "phase": {"equals", "in"},
    "category_set": {"equals", "in", "contains_category"},
    "detector_id_set": {"equals", "in"},
    "risk_score": {"equals", "in", "greater_or_equal", "less_or_equal"},
    "severity": {"equals", "in"},
    "confidence_band": {"equals", "in"},
    "application_id": {"equals", "in"},
    "environment_type": {"equals", "in"},
    "source": {"equals", "in"},
}


@dataclass(frozen=True, slots=True)
class PolicyCondition:
    field: str
    operator: str
    value: object

    def __post_init__(self) -> None:
        _validate_condition(self.field, self.operator, self.value)

    def as_dict(self) -> dict[str, object]:
        value = list(self.value) if isinstance(self.value, tuple) else self.value
        return {"field": self.field, "operator": self.operator, "value": value}


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    policy_id: str
    version_id: str
    version: int
    scope_kind: str
    scope_id: str
    phase: str
    priority: int
    enabled: bool
    action: PolicyAction
    rationale_code: str
    condition_mode: str
    conditions: tuple[PolicyCondition, ...]
    redaction_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.scope_kind not in SCOPE_RANK:
            raise PolicyValidationError("invalid policy scope")
        if self.phase not in {"input", "output"}:
            raise PolicyValidationError("invalid policy phase")
        if self.priority < 1:
            raise PolicyValidationError("priority must be positive")
        if self.condition_mode not in {"all", "any"}:
            raise PolicyValidationError("condition group must be all or any")
        if not 1 <= len(self.conditions) <= MAX_CONDITIONS:
            raise PolicyValidationError("condition group must contain 1 to 20 conditions")
        if self.action is PolicyAction.REDACT and not self.redaction_targets:
            raise PolicyValidationError("redact action requires explicit targets")
        categories = {item.value for item in Category}
        if any(target not in categories for target in self.redaction_targets):
            raise PolicyValidationError("invalid redaction target")


@dataclass(frozen=True, slots=True)
class PolicyFacts:
    phase: str
    categories: frozenset[str]
    detector_ids: frozenset[str]
    risk_score: int
    severity: str
    confidence_band: str
    application_id: str
    environment_type: str
    source: str
    organization_id: str
    environment_id: str


@dataclass(frozen=True, slots=True)
class ScopeWinner:
    scope_kind: str
    policy_id: str
    version_id: str
    version: int
    priority: int
    action: PolicyAction
    rationale_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "scope_kind": self.scope_kind,
            "policy_id": self.policy_id,
            "policy_version_id": self.version_id,
            "version": self.version,
            "priority": self.priority,
            "action": self.action.value,
            "rationale_code": self.rationale_code,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecisionResult:
    action: PolicyAction
    selected_policy_id: str | None
    selected_version_id: str | None
    selected_version: int | None
    selected_scope: str | None
    scope_winners: tuple[ScopeWinner, ...]
    evaluated_policy_versions: tuple[dict[str, object], ...]
    rationale_code: str
    redaction_targets: tuple[str, ...] = ()


def evaluate_policies(
    policies: list[PolicySnapshot] | tuple[PolicySnapshot, ...], facts: PolicyFacts
) -> PolicyDecisionResult:
    if facts.phase not in {"input", "output"}:
        raise PolicyEvaluationError("invalid evaluation phase")
    relevant = [policy for policy in policies if policy.enabled and policy.phase == facts.phase]
    _reject_duplicate_priorities(relevant)
    expected_scope = {
        "organization": facts.organization_id,
        "application": facts.application_id,
        "environment": facts.environment_id,
    }
    winners: list[tuple[PolicySnapshot, ScopeWinner]] = []
    evaluated: list[dict[str, object]] = []
    for scope_kind in ("organization", "application", "environment"):
        candidates = sorted(
            (
                policy
                for policy in relevant
                if policy.scope_kind == scope_kind and policy.scope_id == expected_scope[scope_kind]
            ),
            key=lambda item: (item.priority, item.policy_id),
        )
        for policy in candidates:
            evaluated.append(
                {
                    "policy_id": policy.policy_id,
                    "policy_version_id": policy.version_id,
                    "version": policy.version,
                }
            )
            if _matches(policy, facts):
                winner = ScopeWinner(
                    scope_kind=scope_kind,
                    policy_id=policy.policy_id,
                    version_id=policy.version_id,
                    version=policy.version,
                    priority=policy.priority,
                    action=policy.action,
                    rationale_code=policy.rationale_code,
                )
                winners.append((policy, winner))
                break
    if not winners:
        return PolicyDecisionResult(
            action=PolicyAction.ALLOW,
            selected_policy_id=None,
            selected_version_id=None,
            selected_version=None,
            selected_scope=None,
            scope_winners=(),
            evaluated_policy_versions=tuple(evaluated),
            rationale_code="no_policy_matched",
        )
    selected_policy, selected_winner = max(
        winners,
        key=lambda item: (ACTION_RANK[item[0].action], SCOPE_RANK[item[0].scope_kind]),
    )
    return PolicyDecisionResult(
        action=selected_policy.action,
        selected_policy_id=selected_policy.policy_id,
        selected_version_id=selected_policy.version_id,
        selected_version=selected_policy.version,
        selected_scope=selected_winner.scope_kind,
        scope_winners=tuple(winner for _, winner in winners),
        evaluated_policy_versions=tuple(evaluated),
        rationale_code=selected_policy.rationale_code,
        redaction_targets=selected_policy.redaction_targets,
    )


def _matches(policy: PolicySnapshot, facts: PolicyFacts) -> bool:
    results = [_condition_matches(condition, facts) for condition in policy.conditions]
    return all(results) if policy.condition_mode == "all" else any(results)


def _condition_matches(condition: PolicyCondition, facts: PolicyFacts) -> bool:
    actual: object
    if condition.field == "category_set":
        actual = facts.categories
    elif condition.field == "detector_id_set":
        actual = facts.detector_ids
    else:
        actual = getattr(facts, condition.field)
    expected = condition.value
    if condition.operator == "equals":
        if isinstance(actual, frozenset):
            return isinstance(expected, (list, tuple)) and actual == frozenset(expected)
        return actual == expected
    if condition.operator == "in":
        if not isinstance(expected, (list, tuple)):
            raise PolicyEvaluationError("in operator requires a list")
        values = set(expected)
        return bool(actual & values) if isinstance(actual, frozenset) else actual in values
    if condition.operator == "greater_or_equal":
        return isinstance(actual, int) and isinstance(expected, int) and actual >= expected
    if condition.operator == "less_or_equal":
        return isinstance(actual, int) and isinstance(expected, int) and actual <= expected
    if condition.operator == "contains_category":
        return isinstance(actual, frozenset) and expected in actual
    raise PolicyEvaluationError("unsupported policy operator")


def _reject_duplicate_priorities(policies: list[PolicySnapshot]) -> None:
    seen: set[tuple[str, str, str, int]] = set()
    for policy in policies:
        key = (policy.scope_kind, policy.scope_id, policy.phase, policy.priority)
        if key in seen:
            raise PolicyEvaluationError("duplicate policy priority")
        seen.add(key)


def _validate_condition(field: str, operator: str, value: object) -> None:
    if field not in ALLOWED_FIELDS or operator not in FIELD_OPERATORS[field]:
        raise PolicyValidationError("invalid field/operator combination")
    is_list = isinstance(value, (list, tuple))
    values = list(value) if isinstance(value, (list, tuple)) else [value]
    if any(not isinstance(item, (str, int)) or isinstance(item, bool) for item in values):
        raise PolicyValidationError("condition values must be strings or integers")
    if operator == "in" and (not is_list or not 1 <= len(values) <= MAX_LIST_VALUES):
        raise PolicyValidationError("in requires 1 to 20 values")
    if operator != "in" and is_list and field not in {"category_set", "detector_id_set"}:
        raise PolicyValidationError("operator requires a scalar value")
    if field in {"category_set", "detector_id_set"} and operator == "equals" and not is_list:
        raise PolicyValidationError("set equality requires a list")
    if field == "phase" and any(item not in {"input", "output"} for item in values):
        raise PolicyValidationError("invalid phase value")
    categories = {category.value for category in Category}
    if field == "category_set" and any(item not in categories for item in values):
        raise PolicyValidationError("invalid category value")
    if field == "detector_id_set" and any(
        not isinstance(item, str) or not DETECTOR_ID.fullmatch(item) for item in values
    ):
        raise PolicyValidationError("invalid detector identifier")
    if field == "risk_score" and any(
        not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 100
        for item in values
    ):
        raise PolicyValidationError("invalid risk score")
    severities = {severity.value for severity in Severity}
    if field in {"severity", "confidence_band"} and any(item not in severities for item in values):
        raise PolicyValidationError("invalid severity value")
    if field == "application_id":
        try:
            for item in values:
                UUID(str(item))
        except ValueError as error:
            raise PolicyValidationError("invalid application identifier") from error
    if field == "environment_type" and any(
        item not in {"development", "staging", "production"} for item in values
    ):
        raise PolicyValidationError("invalid environment type")
    if field == "source" and any(
        item not in {"analyze", "playground", "gateway"} for item in values
    ):
        raise PolicyValidationError("invalid source")
