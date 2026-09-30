"""Pure, versioned Phase 3 risk arithmetic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from renzai.modules.security.domain.types import Category, Direction, Severity

RISK_PROFILE_NAME = "renzai-v1"
RISK_PROFILE_VERSION = 1
RISK_FORMULA_VERSION = "1.0.0"
SYSTEM_RISK_PROFILE_ID = "71000000-0000-7000-8000-000000000001"
SYSTEM_RISK_PROFILE_VERSION_ID = "71000000-0000-7000-8000-000000000002"

BASE_WEIGHTS: Mapping[Category, int] = MappingProxyType(
    {
        Category.PROMPT_INJECTION: 55,
        Category.INSTRUCTION_OVERRIDE: 45,
        Category.SYSTEM_PROMPT_EXTRACTION: 55,
        Category.JAILBREAK: 50,
        Category.ROLE_MANIPULATION: 40,
        Category.ENCODED_OBFUSCATED: 35,
        Category.SECRET_EXPOSURE: 80,
        Category.PII_EXPOSURE: 55,
        Category.SUSPICIOUS_URL: 20,
        Category.TOOL_MANIPULATION_INDICATOR: 45,
        Category.DATA_EXFILTRATION_INDICATOR: 60,
    }
)


@dataclass(frozen=True, slots=True)
class RiskProfileSnapshot:
    profile_id: str
    version_id: str
    name: str
    version: int
    formula_version: str
    weights: Mapping[Category, int]


@dataclass(frozen=True, slots=True)
class RiskFinding:
    finding_id: str
    category: Category
    detector_id: str
    detector_version: str
    confidence: int
    direction: Direction
    normalized_start: int | None
    normalized_end: int | None
    overlap_group: str | None


@dataclass(frozen=True, slots=True)
class RiskContributionResult:
    finding_id: str
    category: Category
    detector_id: str
    detector_version: str
    base_weight: int
    confidence: int
    raw_contribution: int
    overlap_group: str
    retained: bool
    suppressed_by_finding_id: str | None
    corroboration_bonus: int
    critical_floor_applied: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "finding_id": self.finding_id,
            "category": self.category.value,
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "base_weight": self.base_weight,
            "confidence": self.confidence,
            "raw_contribution": self.raw_contribution,
            "overlap_group": self.overlap_group,
            "status": "retained" if self.retained else "suppressed",
            "suppressed_by_finding_id": self.suppressed_by_finding_id,
            "corroboration_bonus": self.corroboration_bonus,
            "critical_floor_applied": self.critical_floor_applied,
        }


@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    risk_score: int
    severity: Severity
    confidence: int
    base_score: int
    corroboration_bonus: int
    critical_floor: int
    contributions: tuple[RiskContributionResult, ...]
    profile: RiskProfileSnapshot


@dataclass(frozen=True, slots=True)
class _Candidate:
    finding: RiskFinding
    base_weight: int
    raw: int
    group: str


def renzai_v1_profile() -> RiskProfileSnapshot:
    return RiskProfileSnapshot(
        profile_id=SYSTEM_RISK_PROFILE_ID,
        version_id=SYSTEM_RISK_PROFILE_VERSION_ID,
        name=RISK_PROFILE_NAME,
        version=RISK_PROFILE_VERSION,
        formula_version=RISK_FORMULA_VERSION,
        weights=BASE_WEIGHTS,
    )


def severity_for_score(score: int) -> Severity:
    if score >= 75:
        return Severity.CRITICAL
    if score >= 50:
        return Severity.HIGH
    if score >= 25:
        return Severity.MEDIUM
    return Severity.LOW


def confidence_band(confidence: int) -> Severity:
    return severity_for_score(confidence)


def evaluate_risk(
    findings: list[RiskFinding] | tuple[RiskFinding, ...], profile: RiskProfileSnapshot
) -> RiskEvaluation:
    candidates: list[_Candidate] = []
    for finding in findings:
        if not 0 <= finding.confidence <= 100:
            raise ValueError("finding confidence must be between 0 and 100")
        try:
            base_weight = profile.weights[finding.category]
        except KeyError as error:
            raise ValueError(f"profile has no weight for {finding.category.value}") from error
        raw = (base_weight * finding.confidence + 50) // 100
        candidates.append(_Candidate(finding, base_weight, raw, _group_key(finding)))

    grouped: dict[str, list[_Candidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.group, []).append(candidate)

    retained: list[_Candidate] = []
    retained_by_group: dict[str, _Candidate] = {}
    for group, members in grouped.items():
        strongest = sorted(
            members,
            key=lambda item: (
                -item.raw,
                -item.finding.confidence,
                item.finding.detector_id,
                item.finding.finding_id,
            ),
        )[0]
        retained.append(strongest)
        retained_by_group[group] = strongest
    retained.sort(
        key=lambda item: (
            -item.raw,
            -item.finding.confidence,
            item.finding.category.value,
            item.finding.detector_id,
            item.finding.finding_id,
        )
    )

    highest = retained[0] if retained else None
    second = retained[1] if len(retained) > 1 else None
    bonus = 0
    if (
        highest is not None
        and second is not None
        and highest.finding.category is not second.finding.category
        and _non_overlapping(highest.finding, second.finding)
    ):
        bonus = min(25, second.raw // 2)
    base_score = min(100, (highest.raw if highest else 0) + bonus)
    floor_candidates = {
        candidate.finding.finding_id
        for candidate in candidates
        if candidate.finding.direction is Direction.OUTPUT
        and candidate.finding.category is Category.SECRET_EXPOSURE
        and candidate.finding.detector_id == "secrets.api_key"
        and candidate.finding.confidence >= 90
    }
    critical_floor = 80 if floor_candidates else 0
    risk_score = min(100, max(base_score, critical_floor))

    contributions = tuple(
        RiskContributionResult(
            finding_id=candidate.finding.finding_id,
            category=candidate.finding.category,
            detector_id=candidate.finding.detector_id,
            detector_version=candidate.finding.detector_version,
            base_weight=candidate.base_weight,
            confidence=candidate.finding.confidence,
            raw_contribution=candidate.raw,
            overlap_group=candidate.group,
            retained=retained_by_group[candidate.group] is candidate,
            suppressed_by_finding_id=(
                None
                if retained_by_group[candidate.group] is candidate
                else retained_by_group[candidate.group].finding.finding_id
            ),
            corroboration_bonus=(bonus if highest is candidate else 0),
            critical_floor_applied=candidate.finding.finding_id in floor_candidates,
        )
        for candidate in sorted(
            candidates,
            key=lambda item: (
                -item.raw,
                item.finding.category.value,
                item.finding.detector_id,
                item.finding.finding_id,
            ),
        )
    )
    return RiskEvaluation(
        risk_score=risk_score,
        severity=severity_for_score(risk_score),
        confidence=highest.finding.confidence if highest else 0,
        base_score=base_score,
        corroboration_bonus=bonus,
        critical_floor=critical_floor,
        contributions=contributions,
        profile=profile,
    )


def _group_key(finding: RiskFinding) -> str:
    if finding.overlap_group:
        return finding.overlap_group
    if (
        finding.normalized_start is not None
        and finding.normalized_end is not None
        and finding.normalized_start < finding.normalized_end
    ):
        return f"span:{finding.normalized_start}:{finding.normalized_end}:{finding.finding_id}"
    return "spanless:analysis"


def _non_overlapping(left: RiskFinding, right: RiskFinding) -> bool:
    if (
        left.normalized_start is None
        or left.normalized_end is None
        or right.normalized_start is None
        or right.normalized_end is None
    ):
        return False
    return (
        left.normalized_end <= right.normalized_start
        or right.normalized_end <= left.normalized_start
    )
