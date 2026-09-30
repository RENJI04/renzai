"""Framework-independent deterministic detector orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns

from renzai.modules.security.domain.aggregation import aggregate
from renzai.modules.security.domain.detectors import DETECTOR_REGISTRY, RULESET_VERSION
from renzai.modules.security.domain.normalization import (
    NORMALIZATION_VERSION,
    NormalizationBudget,
    normalize,
)
from renzai.modules.security.domain.redaction import PLACEHOLDERS, RedactionSpan, redact
from renzai.modules.security.domain.types import (
    Detector,
    DetectorFinding,
    DetectorInput,
    Direction,
    InspectionFailure,
    NormalizedContent,
)


@dataclass(frozen=True, slots=True)
class Timing:
    normalization_ms: int
    detector_ms: int
    total_ms: int


@dataclass(frozen=True, slots=True)
class AnalysisComputation:
    normalized: NormalizedContent
    findings: tuple[DetectorFinding, ...]
    redacted_content: str
    timing: Timing
    normalization_version: str = NORMALIZATION_VERSION
    ruleset_version: str = RULESET_VERSION


def render_redacted(
    computation: AnalysisComputation, categories: frozenset[str] | None = None
) -> tuple[str, bool]:
    findings = tuple(
        finding
        for finding in computation.findings
        if categories is None or finding.category.value in categories
    )
    spans = [
        RedactionSpan(
            finding.normalized_start,
            finding.normalized_end,
            finding.redaction_type,
        )
        for finding in findings
        if finding.redaction_type is not None
        and finding.normalized_start is not None
        and finding.normalized_end is not None
        and finding.metadata.get("transform") == "unicode_nfkc_whitespace"
    ]
    transformed_sensitive = [
        finding.redaction_type
        for finding in findings
        if finding.redaction_type is not None
        and finding.metadata.get("transform") != "unicode_nfkc_whitespace"
    ]
    if transformed_sensitive:
        priority = {"SECRET": 4, "API_KEY": 3, "EMAIL": 2, "PHONE": 1}
        try:
            strongest = max(transformed_sensitive, key=lambda item: priority[item])
        except KeyError as error:
            raise InspectionFailure("detector returned an invalid redaction type") from error
        return PLACEHOLDERS[strongest], True
    return redact(computation.normalized.primary.text, spans), bool(spans)


class SecurityEngine:
    def __init__(
        self,
        detectors: tuple[Detector, ...] = DETECTOR_REGISTRY,
        budget: NormalizationBudget | None = None,
    ) -> None:
        self.detectors = detectors
        self.budget = budget or NormalizationBudget()

    def analyze(self, content: str, direction: Direction) -> AnalysisComputation:
        started = perf_counter_ns()
        normalized = normalize(content, self.budget)
        normalized_at = perf_counter_ns()
        raw_findings: list[DetectorFinding] = []
        detector_input = DetectorInput(content=normalized, direction=direction)
        for detector in self.detectors:
            try:
                raw_findings.extend(detector.detect(detector_input))
            except Exception as error:
                if detector.required:
                    raise InspectionFailure(
                        f"required detector failed: {detector.detector_id}"
                    ) from error
        findings = aggregate(raw_findings)
        detected_at = perf_counter_ns()
        finished = perf_counter_ns()
        computation = AnalysisComputation(
            normalized=normalized,
            findings=findings,
            redacted_content="",
            timing=Timing(
                normalization_ms=(normalized_at - started) // 1_000_000,
                detector_ms=(detected_at - normalized_at) // 1_000_000,
                total_ms=(finished - started) // 1_000_000,
            ),
        )
        redacted_content, _ = render_redacted(computation)
        return AnalysisComputation(
            normalized=computation.normalized,
            findings=computation.findings,
            redacted_content=redacted_content,
            timing=computation.timing,
        )
