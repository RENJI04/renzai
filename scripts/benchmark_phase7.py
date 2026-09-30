"""Repeatable microbenchmark for Phase 7 pure-domain incremental cost."""

from timeit import timeit

from renzai.modules.policies.domain import (
    PolicyAction,
    PolicyCondition,
    PolicyFacts,
    PolicySnapshot,
    evaluate_policies,
)
from renzai.modules.risk.domain import (
    RiskFinding,
    evaluate_risk,
    renzai_v1_profile,
)
from renzai.modules.security.domain.types import Category, Direction


def finding(index: int, category: Category = Category.PROMPT_INJECTION) -> RiskFinding:
    return RiskFinding(
        finding_id=str(index),
        category=category,
        detector_id=f"benchmark.{index}",
        detector_version="1.0.0",
        confidence=95,
        direction=Direction.INPUT,
        normalized_start=index * 20,
        normalized_end=index * 20 + 8,
        overlap_group=None,
    )


FACTS = PolicyFacts(
    phase="input",
    categories=frozenset({"prompt_injection"}),
    detector_ids=frozenset({"benchmark.1"}),
    risk_score=52,
    severity="high",
    confidence_band="critical",
    application_id="00000000-0000-0000-0000-000000000001",
    environment_type="production",
    source="analyze",
    organization_id="00000000-0000-0000-0000-000000000002",
    environment_id="00000000-0000-0000-0000-000000000003",
)


def policies(count: int) -> list[PolicySnapshot]:
    return [
        PolicySnapshot(
            policy_id=str(index),
            version_id=f"v{index}",
            version=1,
            scope_kind="organization",
            scope_id=FACTS.organization_id,
            phase="input",
            priority=index + 1,
            enabled=True,
            action=PolicyAction.FLAG,
            rationale_code="benchmark",
            condition_mode="all",
            conditions=(
                PolicyCondition("risk_score", "greater_or_equal", 100 if index < count - 1 else 0),
            ),
        )
        for index in range(count)
    ]


def report(label: str, operation: object, iterations: int) -> None:
    if not callable(operation):
        raise TypeError("operation must be callable")
    elapsed = timeit(operation, number=iterations)
    print(f"{label}: {elapsed / iterations * 1_000_000:.2f} us/op")


def main() -> None:
    profile = renzai_v1_profile()
    report("risk_0_findings", lambda: evaluate_risk([], profile), 10_000)
    report("risk_1_finding", lambda: evaluate_risk([finding(1)], profile), 10_000)
    report(
        "risk_3_findings",
        lambda: evaluate_risk(
            [
                finding(1),
                finding(2, Category.SYSTEM_PROMPT_EXTRACTION),
                finding(3, Category.DATA_EXFILTRATION_INDICATOR),
            ],
            profile,
        ),
        10_000,
    )
    for count in (10, 100):
        snapshots = policies(count)
        report(
            f"policy_{count}_worst_case",
            lambda rows=snapshots: evaluate_policies(rows, FACTS),
            5_000,
        )


if __name__ == "__main__":
    main()
