"""Detection, risk, and policy use case shared by Analyze and Playground."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.config import PrivacyMode
from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.infrastructure.observability.metrics import record_security_operation
from renzai.modules.applications.models import Application
from renzai.modules.policies.application import PolicyService
from renzai.modules.policies.domain import (
    PolicyEvaluationError,
    PolicyFacts,
    evaluate_policies,
)
from renzai.modules.policies.models import PolicyDecision
from renzai.modules.risk.application import ensure_system_risk_profile
from renzai.modules.risk.domain import RiskFinding, confidence_band, evaluate_risk
from renzai.modules.risk.models import RiskContribution
from renzai.modules.security.domain.engine import (
    AnalysisComputation,
    SecurityEngine,
    render_redacted,
)
from renzai.modules.security.domain.types import Direction, InspectionFailure
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent

CAPABILITIES: dict[str, object] = {
    "detection": {"evaluated": True, "version": "1.0.0"},
    "risk_scoring": {"evaluated": True, "profile": "renzai-v1", "version": 1},
    "policy": {"evaluated": True, "grammar_version": "1.0.0"},
}


@dataclass(frozen=True, slots=True)
class AnalysisScope:
    organization_id: UUID
    application_id: UUID
    environment_id: UUID
    environment_type: str
    correlation_id: str


class AnalysisService:
    def __init__(self, db: AsyncSession, engine: SecurityEngine | None = None) -> None:
        self.db = db
        self.engine = engine or SecurityEngine()

    async def analyze(
        self,
        scope: AnalysisScope,
        application: Application,
        content: str,
        direction: Direction,
        source: str,
    ) -> dict[str, object]:
        computation = self.engine.analyze(content, direction)
        event_id = new_uuid7()
        analysis_id = new_uuid7()
        finding_ids = [new_uuid7() for _ in computation.findings]
        try:
            profile = await ensure_system_risk_profile(self.db)
            risk_started = perf_counter_ns()
            risk = evaluate_risk(
                [
                    RiskFinding(
                        finding_id=str(finding_id),
                        category=domain_finding.category,
                        detector_id=domain_finding.detector_id,
                        detector_version=domain_finding.detector_version,
                        confidence=domain_finding.confidence,
                        direction=domain_finding.direction,
                        normalized_start=domain_finding.normalized_start,
                        normalized_end=domain_finding.normalized_end,
                        overlap_group=domain_finding.overlap_group,
                    )
                    for finding_id, domain_finding in zip(
                        finding_ids, computation.findings, strict=True
                    )
                ],
                profile,
            )
            risk_ms = (perf_counter_ns() - risk_started) // 1_000_000
            policy_started = perf_counter_ns()
            policies = await PolicyService(self.db).active_snapshots(
                scope.organization_id,
                scope.application_id,
                scope.environment_id,
                direction.value,
            )
            decision = evaluate_policies(
                policies,
                PolicyFacts(
                    phase=direction.value,
                    categories=frozenset(item.category.value for item in computation.findings),
                    detector_ids=frozenset(item.detector_id for item in computation.findings),
                    risk_score=risk.risk_score,
                    severity=risk.severity.value,
                    confidence_band=confidence_band(risk.confidence).value,
                    application_id=str(scope.application_id),
                    environment_type=scope.environment_type,
                    source=source,
                    organization_id=str(scope.organization_id),
                    environment_id=str(scope.environment_id),
                ),
            )
            policy_ms = (perf_counter_ns() - policy_started) // 1_000_000
        except (PolicyEvaluationError, ValueError, LookupError) as error:
            raise InspectionFailure("risk or policy evaluation failed") from error

        redacted_result: str | None = None
        redaction_failure: InspectionFailure | None = None
        if decision.action.value == "redact":
            try:
                redacted_result, applied = render_redacted(
                    computation, frozenset(decision.redaction_targets)
                )
                if not applied:
                    redaction_failure = InspectionFailure(
                        "redact policy has no validated redaction target"
                    )
            except InspectionFailure as error:
                redaction_failure = error

        persisted_content = self._persisted_content(application, content, computation)
        completed_at = utc_now()
        event = SecurityEvent(
            event_id=event_id,
            organization_id=scope.organization_id,
            application_id=scope.application_id,
            environment_id=scope.environment_id,
            direction=direction.value,
            source=source,
            correlation_id=scope.correlation_id,
            privacy_mode=application.privacy_mode,
            content=persisted_content,
            content_bytes=len(content.encode("utf-8")),
            retention_days=application.security_retention_days,
            action=decision.action.value,
            risk_score=risk.risk_score,
            risk_severity=risk.severity.value,
            risk_profile_id=UUID(profile.profile_id),
            risk_profile_version=profile.version,
            selected_policy_id=(
                UUID(decision.selected_policy_id) if decision.selected_policy_id else None
            ),
            selected_policy_version_id=(
                UUID(decision.selected_version_id) if decision.selected_version_id else None
            ),
        )
        total_ms = computation.timing.total_ms + risk_ms + policy_ms
        result = AnalysisResult(
            analysis_id=analysis_id,
            event_id=event_id,
            completed_at=completed_at,
            normalization_version=computation.normalization_version,
            ruleset_version=computation.ruleset_version,
            status="completed",
            finding_count=len(computation.findings),
            normalization_ms=computation.timing.normalization_ms,
            detector_ms=computation.timing.detector_ms,
            total_ms=total_ms,
            capabilities=CAPABILITIES,
            risk_profile_id=UUID(profile.profile_id),
            risk_profile_version_id=UUID(profile.version_id),
            risk_profile_version=profile.version,
            risk_score=risk.risk_score,
            risk_severity=risk.severity.value,
            risk_confidence=risk.confidence,
            base_score=risk.base_score,
            corroboration_bonus=risk.corroboration_bonus,
            critical_floor=risk.critical_floor,
            action=decision.action.value,
            risk_ms=risk_ms,
            policy_ms=policy_ms,
        )
        self.db.add_all([event, result])

        response_findings: list[dict[str, object]] = []
        for finding_id, domain_finding in zip(finding_ids, computation.findings, strict=True):
            evidence = self._storage_evidence(
                application.privacy_mode, domain_finding.as_dict()["evidence"]
            )
            self.db.add(
                Finding(
                    finding_id=finding_id,
                    analysis_id=analysis_id,
                    detector_id=domain_finding.detector_id,
                    detector_version=domain_finding.detector_version,
                    ruleset_version=domain_finding.ruleset_version,
                    category=domain_finding.category.value,
                    direction=domain_finding.direction.value,
                    severity=domain_finding.severity.value,
                    confidence=domain_finding.confidence,
                    evidence=evidence,
                    safe_explanation=domain_finding.safe_explanation,
                    safe_metadata=domain_finding.metadata,
                    overlap_group=domain_finding.overlap_group,
                )
            )
            item = domain_finding.as_dict()
            item["finding_id"] = str(finding_id)
            response_findings.append(item)

        for contribution in risk.contributions:
            self.db.add(
                RiskContribution(
                    contribution_id=new_uuid7(),
                    analysis_id=analysis_id,
                    finding_id=UUID(contribution.finding_id),
                    category=contribution.category.value,
                    detector_id=contribution.detector_id,
                    detector_version=contribution.detector_version,
                    base_weight=contribution.base_weight,
                    confidence=contribution.confidence,
                    raw_contribution=contribution.raw_contribution,
                    overlap_group=contribution.overlap_group,
                    status="retained" if contribution.retained else "suppressed",
                    suppressed_by_finding_id=(
                        UUID(contribution.suppressed_by_finding_id)
                        if contribution.suppressed_by_finding_id
                        else None
                    ),
                    corroboration_bonus=contribution.corroboration_bonus,
                    critical_floor_applied=contribution.critical_floor_applied,
                )
            )
        policy_decision_id = new_uuid7()
        self.db.add(
            PolicyDecision(
                policy_decision_id=policy_decision_id,
                analysis_id=analysis_id,
                risk_profile_version_id=UUID(profile.version_id),
                phase=direction.value,
                action=decision.action.value,
                selected_policy_id=(
                    UUID(decision.selected_policy_id) if decision.selected_policy_id else None
                ),
                selected_policy_version_id=(
                    UUID(decision.selected_version_id) if decision.selected_version_id else None
                ),
                scope_winners=[winner.as_dict() for winner in decision.scope_winners],
                evaluated_policy_versions=list(decision.evaluated_policy_versions),
                rationale_code=decision.rationale_code,
            )
        )
        try:
            await self.db.commit()
        except SQLAlchemyError as error:
            await self.db.rollback()
            raise InspectionFailure("analysis persistence failed") from error

        record_security_operation("analysis", decision.action.value)

        if redaction_failure is not None:
            raise InspectionFailure(
                str(redaction_failure), analysis_id=str(analysis_id)
            ) from redaction_failure

        no_findings = not response_findings
        response: dict[str, object] = {
            "analysis_id": str(analysis_id),
            "event_id": str(event_id),
            "timestamp": completed_at.isoformat(),
            "direction": direction.value,
            "source": source,
            "safe": no_findings and risk.risk_score == 0,
            "no_detected_threat": no_findings and risk.risk_score == 0,
            "action": decision.action.value,
            "risk_score": risk.risk_score,
            "severity": risk.severity.value,
            "confidence": risk.confidence,
            "risk_profile": {
                "id": profile.profile_id,
                "name": profile.name,
                "version": profile.version,
                "formula_version": profile.formula_version,
            },
            "normalization_version": computation.normalization_version,
            "detector_ruleset_version": computation.ruleset_version,
            "findings": response_findings,
            "risk_contributions": [item.as_dict() for item in risk.contributions],
            "risk_explanation": {
                "base_score": risk.base_score,
                "corroboration_bonus": risk.corroboration_bonus,
                "critical_floor": risk.critical_floor,
            },
            "policy_decision": {
                "policy_decision_id": str(policy_decision_id),
                "policy_match": (
                    {
                        "policy_id": decision.selected_policy_id,
                        "policy_version_id": decision.selected_version_id,
                        "version": decision.selected_version,
                        "scope_kind": decision.selected_scope,
                    }
                    if decision.selected_policy_id
                    else None
                ),
                "evaluated_policy_versions": list(decision.evaluated_policy_versions),
                "scope_winners": [winner.as_dict() for winner in decision.scope_winners],
                "rationale_code": decision.rationale_code,
                "redaction_targets": list(decision.redaction_targets),
            },
            "timing": {
                "normalization_ms": computation.timing.normalization_ms,
                "detector_ms": computation.timing.detector_ms,
                "risk_ms": risk_ms,
                "policy_ms": policy_ms,
                "total_ms": total_ms,
            },
            "correlation_id": scope.correlation_id,
        }
        if redacted_result is not None:
            response["redacted_content"] = redacted_result
        return response

    @staticmethod
    def _persisted_content(
        application: Application, original: str, computation: AnalysisComputation
    ) -> str | None:
        safe = not computation.findings
        if safe and not application.safe_content_persistence:
            return None
        mode = PrivacyMode(application.privacy_mode)
        if mode is PrivacyMode.METADATA_ONLY:
            return None
        if mode is PrivacyMode.FULL:
            return original
        return computation.redacted_content

    @staticmethod
    def _storage_evidence(mode: str, evidence: object) -> dict[str, object]:
        if not isinstance(evidence, dict):
            raise InspectionFailure("finding evidence is invalid")
        if mode == PrivacyMode.METADATA_ONLY.value:
            return {"kind": "classification_only", "label": "finding_detected"}
        return evidence
