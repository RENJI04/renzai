"""Optional advisory AI intelligence use cases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import (
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    NotFoundOrHiddenError,
    ValidationError,
)
from renzai.core.ids import new_uuid7
from renzai.core.request_context import get_request_id
from renzai.core.time import utc_now
from renzai.infrastructure.crypto.ai_credentials import AICredentialKeyRing, ai_credential_context
from renzai.infrastructure.http.ai_openai_compatible import AIProviderRuntimeConfig
from renzai.infrastructure.http.outbound import OutboundTargetGuard
from renzai.modules.ai_intelligence.domain import (
    INPUT_CONTEXT_VERSION,
    OUTPUT_SCHEMA_VERSION,
    PROMPT_TEMPLATE_VERSIONS,
    AIDisclosureRevoked,
    AIIntelligenceProvider,
    AIOutputError,
    AIProviderFailure,
    AITaskType,
    DisclosureMode,
    parse_task_output,
)
from renzai.modules.ai_intelligence.models import (
    AIIntelligenceConfiguration,
    AIIntelligenceRequest,
    AIIntelligenceResult,
)
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AuditEvent
from renzai.modules.environments.models import Environment
from renzai.modules.incidents.models import Incident
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.policies.models import PolicyDecision
from renzai.modules.providers.domain import ProviderConfigurationFailure
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.users.models import User

AI_CONFIG_EDITORS = {MembershipRole.OWNER, MembershipRole.ADMIN}
AI_REQUESTERS = {MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.SECURITY_ANALYST}
AI_KINDS = {"openai_compatible_remote", "openai_compatible_local"}

_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
_API_KEY = re.compile(r"(?i)\b(?:sk|rk|pk|api)[-_][A-Za-z0-9_-]{12,}\b")
_SECRET = re.compile(r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]{6,}")


@dataclass(frozen=True, slots=True)
class ProcessResult:
    request_id: UUID
    status: str


class AIConfigurationService:
    def __init__(
        self,
        db: AsyncSession,
        key_ring: AICredentialKeyRing,
        target_guard: OutboundTargetGuard,
        provider: object,
    ) -> None:
        self.db = db
        self.key_ring = key_ring
        self.target_guard = target_guard
        self.provider = provider

    async def create(
        self,
        actor: Membership,
        user: User,
        *,
        application_id: UUID | None,
        environment_id: UUID | None,
        name: str,
        kind: str,
        base_url: str,
        model: str,
        credential: str | None,
        allow_full_content: bool,
        connect_timeout_seconds: int,
        request_timeout_seconds: int,
        response_max_bytes: int,
    ) -> AIIntelligenceConfiguration:
        self.require_editor(actor)
        await self._require_scope(actor.organization_id, application_id, environment_id)
        self._validate(kind, credential, name, model)
        self._validate_credential(credential)
        try:
            target = await self.target_guard.resolve(base_url, kind)
        except ProviderConfigurationFailure as error:
            raise ValidationError(details={"fields": ["base_url"]}) from error
        config_id = new_uuid7()
        encrypted = (
            self.key_ring.encrypt(
                credential, ai_credential_context(config_id, actor.organization_id)
            )
            if credential
            else None
        )
        clean_name = _clean(name)
        row = AIIntelligenceConfiguration(
            config_id=config_id,
            organization_id=actor.organization_id,
            application_id=application_id,
            environment_id=environment_id,
            name=clean_name,
            name_key=clean_name.casefold(),
            kind=kind,
            base_url=target.url,
            model=_clean(model),
            credential_ciphertext=encrypted.ciphertext if encrypted else None,
            credential_key_id=encrypted.key_id if encrypted else None,
            allow_full_content=allow_full_content,
            connect_timeout_seconds=connect_timeout_seconds,
            request_timeout_seconds=request_timeout_seconds,
            response_max_bytes=response_max_bytes,
        )
        self.db.add(row)
        self._audit(actor, user, "ai_provider.created", row)
        await self._commit_conflict()
        return row

    async def list(self, organization_id: UUID) -> list[AIIntelligenceConfiguration]:
        return list(
            (
                await self.db.execute(
                    select(AIIntelligenceConfiguration)
                    .where(AIIntelligenceConfiguration.organization_id == organization_id)
                    .order_by(AIIntelligenceConfiguration.created_at.desc())
                )
            ).scalars()
        )

    async def get(self, organization_id: UUID, config_id: UUID) -> AIIntelligenceConfiguration:
        row = (
            await self.db.execute(
                select(AIIntelligenceConfiguration).where(
                    AIIntelligenceConfiguration.organization_id == organization_id,
                    AIIntelligenceConfiguration.config_id == config_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundOrHiddenError()
        return row

    async def update(
        self,
        actor: Membership,
        user: User,
        row: AIIntelligenceConfiguration,
        *,
        name: str | None,
        model: str | None,
        credential: str | None,
        allow_full_content: bool | None,
    ) -> AIIntelligenceConfiguration:
        self.require_editor(actor)
        if name is not None:
            row.name = _clean(name)
            row.name_key = row.name.casefold()
        if model is not None:
            row.model = _clean(model)
        if credential is not None:
            self._validate_credential(credential)
            encrypted = self.key_ring.encrypt(
                credential, ai_credential_context(row.config_id, row.organization_id)
            )
            row.credential_ciphertext = encrypted.ciphertext
            row.credential_key_id = encrypted.key_id
        if allow_full_content is not None:
            row.allow_full_content = allow_full_content
        self._audit(actor, user, "ai_provider.updated", row)
        await self._commit_conflict()
        return row

    async def set_enabled(
        self,
        actor: Membership,
        user: User,
        row: AIIntelligenceConfiguration,
        enabled: bool,
    ) -> AIIntelligenceConfiguration:
        self.require_editor(actor)
        row.status = "active" if enabled else "disabled"
        self._audit(actor, user, "ai_provider.enabled" if enabled else "ai_provider.disabled", row)
        await self.db.commit()
        return row

    async def validate_connection(
        self, actor: Membership, user: User, row: AIIntelligenceConfiguration
    ) -> None:
        self.require_editor(actor)
        check = getattr(self.provider, "check_health", None)
        if check is None:
            raise ConfigurationError(details={"reason": "ai_provider"})
        try:
            await check(runtime_config(row))
        except AIProviderFailure as error:
            raise ConfigurationError(details={"reason": "ai_provider_validation"}) from error
        self._audit(actor, user, "ai_provider.validated", row)
        await self.db.commit()

    @staticmethod
    def require_editor(actor: Membership) -> None:
        if MembershipRole(actor.role) not in AI_CONFIG_EDITORS:
            raise AuthorizationError()

    async def _require_scope(
        self,
        organization_id: UUID,
        application_id: UUID | None,
        environment_id: UUID | None,
    ) -> None:
        if environment_id is not None and application_id is None:
            raise ValidationError(details={"fields": ["environment_id"]})
        if application_id is None:
            return
        query = select(Application.application_id).where(
            Application.organization_id == organization_id,
            Application.application_id == application_id,
        )
        if environment_id is not None:
            query = (
                select(Environment.environment_id)
                .join(
                    Application,
                    and_(
                        Application.application_id == Environment.application_id,
                        Application.organization_id == Environment.organization_id,
                    ),
                )
                .where(
                    Environment.organization_id == organization_id,
                    Environment.application_id == application_id,
                    Environment.environment_id == environment_id,
                )
            )
        if await self.db.scalar(query) is None:
            raise NotFoundOrHiddenError()

    @staticmethod
    def _validate(kind: str, credential: str | None, name: str, model: str) -> None:
        if kind not in AI_KINDS:
            raise ValidationError(details={"fields": ["kind"]})
        if kind == "openai_compatible_remote" and not credential:
            raise ValidationError(details={"fields": ["credential"]})
        if not _clean(name) or not _clean(model):
            raise ValidationError(details={"fields": ["name", "model"]})

    @staticmethod
    def _validate_credential(value: str | None) -> None:
        if value is not None and any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise ValidationError(details={"fields": ["credential"]})

    async def _commit_conflict(self) -> None:
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": ["name"]}) from error

    def _audit(
        self,
        actor: Membership,
        user: User,
        action: str,
        row: AIIntelligenceConfiguration,
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=user.user_id,
                action=action,
                resource_type="ai_intelligence_configuration",
                resource_id=str(row.config_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata={
                    "kind": row.kind,
                    "application_id": str(row.application_id) if row.application_id else None,
                    "environment_id": str(row.environment_id) if row.environment_id else None,
                    "credential_present": row.credential_ciphertext is not None,
                },
            )
        )


class AIIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def request(
        self,
        actor: Membership,
        user: User,
        incident_id: UUID,
        *,
        task_type: AITaskType,
        disclosure_mode: DisclosureMode,
        idempotency_key: str | None,
    ) -> AIIntelligenceRequest:
        if MembershipRole(actor.role) not in AI_REQUESTERS:
            raise AuthorizationError()
        incident = await self._incident(actor.organization_id, incident_id)
        if disclosure_mode is DisclosureMode.FULL and MembershipRole(actor.role) not in {
            MembershipRole.OWNER,
            MembershipRole.ADMIN,
        }:
            raise AuthorizationError()
        existing = await self._existing_request(
            actor.organization_id, incident_id, task_type, idempotency_key
        )
        if existing is not None:
            return existing
        config = await self._select_config(incident)
        effective_mode = self._effective_mode(incident, config, disclosure_mode)
        key = idempotency_key or str(new_uuid7())
        if not 1 <= len(key) <= 128:
            raise ValidationError(details={"fields": ["Idempotency-Key"]})
        row = AIIntelligenceRequest(
            organization_id=actor.organization_id,
            incident_id=incident_id,
            config_id=config.config_id,
            requested_by_user_id=user.user_id,
            task_type=task_type.value,
            status="pending",
            context_mode=effective_mode.value,
            incident_version=incident.version,
            idempotency_key=key,
            request_correlation_id=get_request_id(),
        )
        self.db.add(row)
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=user.user_id,
                action="ai_intelligence.requested",
                resource_type="incident",
                resource_id=str(incident_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata={"task_type": task_type.value, "context_mode": effective_mode.value},
            )
        )
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            existing = await self._existing_request(
                actor.organization_id, incident_id, task_type, idempotency_key
            )
            if existing is not None:
                return existing
            raise ConflictError(details={"reason": "ai_request_duplicate"}) from error
        return row

    async def list_for_incident(
        self, organization_id: UUID, incident_id: UUID
    ) -> list[dict[str, object]]:
        await self._incident(organization_id, incident_id)
        rows = (
            await self.db.execute(
                select(AIIntelligenceRequest, AIIntelligenceResult, AIIntelligenceConfiguration)
                .join(
                    AIIntelligenceConfiguration,
                    AIIntelligenceConfiguration.config_id == AIIntelligenceRequest.config_id,
                )
                .outerjoin(
                    AIIntelligenceResult,
                    AIIntelligenceResult.request_id == AIIntelligenceRequest.request_id,
                )
                .where(
                    AIIntelligenceRequest.organization_id == organization_id,
                    AIIntelligenceRequest.incident_id == incident_id,
                )
                .order_by(AIIntelligenceRequest.created_at.desc())
            )
        ).all()
        return [request_view(request, result, config) for request, result, config in rows]

    async def get(self, organization_id: UUID, request_id: UUID) -> dict[str, object]:
        row = (
            await self.db.execute(
                select(AIIntelligenceRequest, AIIntelligenceResult, AIIntelligenceConfiguration)
                .join(
                    AIIntelligenceConfiguration,
                    AIIntelligenceConfiguration.config_id == AIIntelligenceRequest.config_id,
                )
                .outerjoin(
                    AIIntelligenceResult,
                    AIIntelligenceResult.request_id == AIIntelligenceRequest.request_id,
                )
                .where(
                    AIIntelligenceRequest.organization_id == organization_id,
                    AIIntelligenceRequest.request_id == request_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise NotFoundOrHiddenError()
        return request_view(*row)

    async def mark_dispatch_failed(self, organization_id: UUID, request_id: UUID) -> None:
        await self.db.execute(
            update(AIIntelligenceRequest)
            .where(
                AIIntelligenceRequest.organization_id == organization_id,
                AIIntelligenceRequest.request_id == request_id,
                AIIntelligenceRequest.status == "pending",
            )
            .values(status="failed", error_code="queue_unavailable", completed_at=utc_now())
        )
        await self.db.commit()

    async def _incident(self, organization_id: UUID, incident_id: UUID) -> Incident:
        incident = (
            await self.db.execute(
                select(Incident).where(
                    Incident.organization_id == organization_id,
                    Incident.incident_id == incident_id,
                )
            )
        ).scalar_one_or_none()
        if incident is None:
            raise NotFoundOrHiddenError()
        return incident

    async def _select_config(self, incident: Incident) -> AIIntelligenceConfiguration:
        rows = list(
            (
                await self.db.execute(
                    select(AIIntelligenceConfiguration).where(
                        AIIntelligenceConfiguration.organization_id == incident.organization_id,
                        AIIntelligenceConfiguration.status == "active",
                        or_(
                            AIIntelligenceConfiguration.application_id.is_(None),
                            and_(
                                AIIntelligenceConfiguration.application_id
                                == incident.application_id,
                                or_(
                                    AIIntelligenceConfiguration.environment_id.is_(None),
                                    AIIntelligenceConfiguration.environment_id
                                    == incident.environment_id,
                                ),
                            ),
                        ),
                    )
                )
            ).scalars()
        )
        if not rows:
            raise ConfigurationError(details={"reason": "ai_not_configured"})
        rows.sort(
            key=lambda row: (row.environment_id is not None, row.application_id is not None),
            reverse=True,
        )
        top = rows[0]
        top_rank = (top.environment_id is not None, top.application_id is not None)
        if (
            sum(
                (row.environment_id is not None, row.application_id is not None) == top_rank
                for row in rows
            )
            != 1
        ):
            raise ConfigurationError(details={"reason": "ai_provider_selection"})
        return top

    async def _existing_request(
        self,
        organization_id: UUID,
        incident_id: UUID,
        task_type: AITaskType,
        idempotency_key: str | None,
    ) -> AIIntelligenceRequest | None:
        filters = [
            AIIntelligenceRequest.organization_id == organization_id,
            AIIntelligenceRequest.incident_id == incident_id,
        ]
        if idempotency_key:
            filters = [
                AIIntelligenceRequest.organization_id == organization_id,
                AIIntelligenceRequest.idempotency_key == idempotency_key,
            ]
        else:
            filters.extend(
                [
                    AIIntelligenceRequest.task_type == task_type.value,
                    AIIntelligenceRequest.status.in_(("pending", "running")),
                ]
            )
        return (
            await self.db.execute(
                select(AIIntelligenceRequest)
                .where(*filters)
                .order_by(AIIntelligenceRequest.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    @staticmethod
    def _effective_mode(
        incident: Incident,
        config: AIIntelligenceConfiguration,
        requested: DisclosureMode,
    ) -> DisclosureMode:
        if requested is DisclosureMode.FULL:
            if incident.privacy_mode != "FULL" or not config.allow_full_content:
                raise ValidationError(details={"fields": ["disclosure_mode"]})
            return requested
        if requested is DisclosureMode.REDACTED and incident.privacy_mode == "METADATA_ONLY":
            return DisclosureMode.METADATA_ONLY
        return requested


async def process_ai_request(
    db: AsyncSession,
    provider: AIIntelligenceProvider,
    organization_id: UUID,
    request_id: UUID,
) -> ProcessResult:
    claimed = await db.execute(
        update(AIIntelligenceRequest)
        .where(
            AIIntelligenceRequest.organization_id == organization_id,
            AIIntelligenceRequest.request_id == request_id,
            AIIntelligenceRequest.status == "pending",
        )
        .values(status="running", started_at=utc_now())
    )
    await db.commit()
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        current = await db.scalar(
            select(AIIntelligenceRequest.status).where(
                AIIntelligenceRequest.organization_id == organization_id,
                AIIntelligenceRequest.request_id == request_id,
            )
        )
        if current is None:
            raise NotFoundOrHiddenError()
        return ProcessResult(request_id, current)
    request = await db.scalar(
        select(AIIntelligenceRequest).where(AIIntelligenceRequest.request_id == request_id)
    )
    assert request is not None
    config = await db.scalar(
        select(AIIntelligenceConfiguration).where(
            AIIntelligenceConfiguration.organization_id == organization_id,
            AIIntelligenceConfiguration.config_id == request.config_id,
            AIIntelligenceConfiguration.status == "active",
        )
    )
    try:
        if config is None:
            raise AIProviderFailure("AI provider is unavailable")
        context = await build_safe_context(
            db, request, full_content_allowed=config.allow_full_content
        )
        task_type = AITaskType(request.task_type)
        content, usage = await provider.generate(
            config=runtime_config(config), task_type=task_type, context=context
        )
        payload = parse_task_output(task_type, content)
        db.add(
            AIIntelligenceResult(
                organization_id=organization_id,
                request_id=request_id,
                config_id=config.config_id,
                model=config.model,
                prompt_template_version=PROMPT_TEMPLATE_VERSIONS[task_type],
                input_context_version=INPUT_CONTEXT_VERSION,
                output_schema_version=OUTPUT_SCHEMA_VERSION,
                structured_payload=payload,
                input_tokens=(usage or {}).get("prompt_tokens"),
                output_tokens=(usage or {}).get("completion_tokens"),
                total_tokens=(usage or {}).get("total_tokens"),
            )
        )
        request.status = "completed"
        request.completed_at = utc_now()
        await db.commit()
        return ProcessResult(request_id, "completed")
    except (AIOutputError, AIProviderFailure, ValueError) as error:
        await db.rollback()
        row = await db.scalar(
            select(AIIntelligenceRequest).where(AIIntelligenceRequest.request_id == request_id)
        )
        assert row is not None
        row.status = "failed"
        if isinstance(error, AIOutputError):
            row.error_code = "invalid_ai_output"
        elif isinstance(error, AIDisclosureRevoked):
            row.error_code = "disclosure_revoked"
        else:
            row.error_code = "ai_provider_error"
        row.completed_at = utc_now()
        await db.commit()
        return ProcessResult(request_id, "failed")


async def build_safe_context(
    db: AsyncSession,
    request: AIIntelligenceRequest,
    *,
    full_content_allowed: bool = False,
) -> dict[str, object]:
    incident = await db.scalar(
        select(Incident).where(
            Incident.organization_id == request.organization_id,
            Incident.incident_id == request.incident_id,
        )
    )
    if incident is None:
        raise NotFoundOrHiddenError()
    if request.context_mode == DisclosureMode.FULL.value and (
        incident.privacy_mode != "FULL" or not full_content_allowed
    ):
        raise AIDisclosureRevoked("AI full-content disclosure was revoked")
    context: dict[str, object] = {
        "context_version": INPUT_CONTEXT_VERSION,
        "incident": {
            "incident_id": str(incident.incident_id),
            "version": request.incident_version,
            "status": incident.status,
            "severity": incident.severity,
            "risk_score": incident.risk_score,
            "category": incident.category,
            "detector_id": incident.detector_id,
            "action": incident.action,
            "source": incident.source,
            "direction": incident.direction,
            "application_id": str(incident.application_id) if incident.application_id else None,
            "environment_id": str(incident.environment_id) if incident.environment_id else None,
            "false_positive": incident.status == "false_positive",
        },
        "disclosure_mode": request.context_mode,
        "operator_comments_included": False,
    }
    if incident.primary_analysis_id is None:
        return context
    analysis = await db.scalar(
        select(AnalysisResult).where(AnalysisResult.analysis_id == incident.primary_analysis_id)
    )
    if analysis is None:
        context["source_evidence_state"] = "expired"
        return context
    findings = list(
        (
            await db.execute(
                select(Finding)
                .where(Finding.analysis_id == analysis.analysis_id)
                .order_by(Finding.category, Finding.detector_id)
            )
        ).scalars()
    )
    decision = await db.scalar(
        select(PolicyDecision).where(PolicyDecision.analysis_id == analysis.analysis_id)
    )
    context["deterministic_findings"] = [
        {
            "detector_id": finding.detector_id,
            "detector_version": finding.detector_version,
            "category": finding.category,
            "severity": finding.severity,
            "confidence": finding.confidence,
            **(
                {"safe_explanation": scrub_text(finding.safe_explanation)}
                if request.context_mode != DisclosureMode.METADATA_ONLY.value
                else {}
            ),
        }
        for finding in findings
    ]
    context["risk"] = {
        "score": analysis.risk_score,
        "severity": analysis.risk_severity,
        "confidence": analysis.risk_confidence,
        "profile_version": analysis.risk_profile_version,
    }
    context["policy"] = (
        {
            "action": decision.action,
            "rationale_code": decision.rationale_code,
            "selected_policy_id": str(decision.selected_policy_id)
            if decision.selected_policy_id
            else None,
            "selected_policy_version_id": str(decision.selected_policy_version_id)
            if decision.selected_policy_version_id
            else None,
        }
        if decision
        else None
    )
    if request.context_mode == DisclosureMode.FULL.value:
        event = await db.scalar(
            select(SecurityEvent).where(SecurityEvent.event_id == incident.primary_event_id)
        )
        if event is not None and event.content is not None:
            context["retained_content"] = scrub_text(event.content)
        else:
            context["source_evidence_state"] = "not_retained"
    return context


def scrub_text(value: str) -> str:
    """Remove common secret/PII forms before any external AI request."""

    value = _SECRET.sub("[REDACTED:SECRET]", value)
    value = _API_KEY.sub("[REDACTED:API_KEY]", value)
    value = _EMAIL.sub("[REDACTED:EMAIL]", value)
    return _PHONE.sub("[REDACTED:PHONE]", value)


def runtime_config(row: AIIntelligenceConfiguration) -> AIProviderRuntimeConfig:
    return AIProviderRuntimeConfig(
        config_id=row.config_id,
        organization_id=row.organization_id,
        kind=row.kind,
        base_url=row.base_url,
        model=row.model,
        credential_ciphertext=row.credential_ciphertext,
        credential_key_id=row.credential_key_id,
        connect_timeout_seconds=row.connect_timeout_seconds,
        request_timeout_seconds=row.request_timeout_seconds,
        response_max_bytes=row.response_max_bytes,
    )


def config_view(row: AIIntelligenceConfiguration) -> dict[str, object]:
    return {
        "config_id": str(row.config_id),
        "application_id": str(row.application_id) if row.application_id else None,
        "environment_id": str(row.environment_id) if row.environment_id else None,
        "name": row.name,
        "kind": row.kind,
        "base_url": row.base_url,
        "model": row.model,
        "credential_present": row.credential_ciphertext is not None,
        "allow_full_content": row.allow_full_content,
        "status": row.status,
        "connect_timeout_seconds": row.connect_timeout_seconds,
        "request_timeout_seconds": row.request_timeout_seconds,
        "response_max_bytes": row.response_max_bytes,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def request_view(
    request: AIIntelligenceRequest,
    result: AIIntelligenceResult | None,
    config: AIIntelligenceConfiguration,
) -> dict[str, object]:
    return {
        "request_id": str(request.request_id),
        "incident_id": str(request.incident_id),
        "task_type": request.task_type,
        "status": request.status,
        "ai_generated": True,
        "context_mode": request.context_mode,
        "incident_version": request.incident_version,
        "provider_id": str(config.config_id),
        "provider_name": config.name,
        "model": result.model if result else config.model,
        "prompt_template_version": result.prompt_template_version if result else None,
        "input_context_version": result.input_context_version if result else INPUT_CONTEXT_VERSION,
        "output_schema_version": result.output_schema_version if result else OUTPUT_SCHEMA_VERSION,
        "content": result.structured_payload if result else None,
        "usage": (
            {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
            }
            if result
            else None
        ),
        "error_code": request.error_code,
        "created_at": request.created_at.isoformat(),
        "completed_at": request.completed_at.isoformat() if request.completed_at else None,
    }


def _clean(value: str) -> str:
    return " ".join(value.strip().split())
