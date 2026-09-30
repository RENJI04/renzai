"""Framework-independent contracts for deterministic security analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class Direction(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(StrEnum):
    PROMPT_INJECTION = "prompt_injection"
    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    JAILBREAK = "jailbreak"
    ROLE_MANIPULATION = "role_manipulation"
    ENCODED_OBFUSCATED = "encoded_obfuscated"
    SECRET_EXPOSURE = "secret_exposure"  # noqa: S105 - detector category, not a credential
    PII_EXPOSURE = "pii_exposure"
    SUSPICIOUS_URL = "suspicious_url"
    TOOL_MANIPULATION_INDICATOR = "tool_manipulation_indicator"
    DATA_EXFILTRATION_INDICATOR = "data_exfiltration_indicator"


@dataclass(frozen=True, slots=True)
class NormalizedCandidate:
    text: str
    transform: str
    source_map: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    original: str
    primary: NormalizedCandidate
    candidates: tuple[NormalizedCandidate, ...]
    version: str
    indicators: frozenset[str]


@dataclass(frozen=True, slots=True)
class DetectorInput:
    content: NormalizedContent
    direction: Direction
    safe_context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: str
    text: str | None = None
    start: int | None = None
    end: int | None = None
    normalization_version: str | None = None
    label: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"kind": self.kind}
        for key in ("text", "start", "end", "normalization_version", "label"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result


@dataclass(frozen=True, slots=True)
class DetectorFinding:
    detector_id: str
    detector_version: str
    ruleset_version: str
    category: Category
    direction: Direction
    severity: Severity
    confidence: int
    evidence: Evidence
    safe_explanation: str
    metadata: dict[str, str]
    normalized_start: int | None = None
    normalized_end: int | None = None
    redaction_type: str | None = None
    overlap_group: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "detector_id": self.detector_id,
            "detector_version": self.detector_version,
            "ruleset_version": self.ruleset_version,
            "category": self.category.value,
            "direction": self.direction.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "evidence": self.evidence.as_dict(),
            "safe_explanation": self.safe_explanation,
            "metadata": self.metadata,
            "overlap_group": self.overlap_group,
        }


class Detector(Protocol):
    detector_id: str
    detector_version: str
    required: bool

    def detect(self, detector_input: DetectorInput) -> tuple[DetectorFinding, ...]: ...


class InspectionFailure(RuntimeError):
    """A required deterministic inspection stage did not complete validly."""

    def __init__(self, message: str = "", *, analysis_id: str | None = None) -> None:
        super().__init__(message)
        self.analysis_id = analysis_id
