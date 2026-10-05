"""Incident creation, query, lifecycle, assignment, comments, and timeline use cases."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from renzai.core.errors import (
    AuthorizationError,
    ConflictError,
    InvalidTransitionError,
    NotFoundOrHiddenError,
    ValidationError,
)
from renzai.core.ids import new_uuid7
from renzai.core.request_context import get_request_id
from renzai.core.time import utc_now
from renzai.infrastructure.observability.metrics import record_security_operation
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AuditEvent
from renzai.modules.environments.models import Environment
from renzai.modules.incidents.domain import (
    INCIDENT_EDITORS,
    TERMINAL_STATUSES,
    IncidentSeverity,
    IncidentStatus,
    automatic_summary,
    automatic_title,
    can_comment_on_incident,
    can_edit_incident,
    normalize_plain_text,
    validate_transition,
)
from renzai.modules.incidents.models import (
    Incident,
    IncidentComment,
    IncidentSecurityEvent,
    IncidentTimelineEvent,
)
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.policies.models import PolicyDecision
from renzai.modules.security.domain.engine import SecurityEngine
from renzai.modules.security.domain.types import Direction, InspectionFailure
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.users.models import User

AUTOMATIC_ACTIONS = frozenset({"block", "require_review"})
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class IncidentPersistenceFailure(RuntimeError):
    pass


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_from_analysis(
        self, organization_id: UUID, analysis_id: UUID, correlation_id: str
    ) -> Incident:
        row = (
            await self.db.execute(
                select(SecurityEvent, AnalysisResult)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .where(
                    SecurityEvent.organization_id == organization_id,
                    AnalysisResult.analysis_id == analysis_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise NotFoundOrHiddenError()
        event, analysis = row
        if event.source != "gateway" or analysis.action not in AUTOMATIC_ACTIONS:
            raise ValidationError(details={"fields": ["analysis_id"]})

        finding = await self._primary_finding(analysis.analysis_id)
        trigger_rule_id = self._trigger_rule(event, analysis)
        event_id = event.event_id
        existing = await self._automatic_existing(organization_id, event_id, trigger_rule_id)
        if existing is not None:
            record_security_operation("incident", "automatic_deduplicated")
            return existing

        severity = IncidentSeverity(str(analysis.risk_severity))
        category = finding.category if finding is not None else None
        now = utc_now()
        incident = Incident(
            incident_id=new_uuid7(),
            organization_id=organization_id,
            application_id=event.application_id,
            environment_id=event.environment_id,
            primary_event_id=event_id,
            primary_analysis_id=analysis.analysis_id,
            trigger_rule_id=trigger_rule_id,
            status=IncidentStatus.OPEN.value,
            severity=severity.value,
            risk_score=analysis.risk_score,
            category=category,
            detector_id=finding.detector_id if finding is not None else None,
            action=str(analysis.action),
            source=event.source,
            direction=event.direction,
            title=automatic_title(severity, category, str(analysis.action)),
            safe_summary=automatic_summary(
                source=event.source,
                direction=event.direction,
                action=str(analysis.action),
                category=category,
                risk_score=int(analysis.risk_score or 0),
            ),
            privacy_mode=event.privacy_mode,
            security_retention_days=event.retention_days,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.db.add(incident)
        self.db.add(
            IncidentSecurityEvent(
                organization_id=organization_id,
                incident_id=incident.incident_id,
                event_id=event_id,
                analysis_id=analysis.analysis_id,
                reason="automatic_policy_escalation",
            )
        )
        self._timeline(
            incident,
            "incident_created",
            "Incident created from a Gateway policy action.",
            actor_type="service",
            correlation_id=correlation_id,
            referenced_event_id=event_id,
            referenced_policy_version_id=event.selected_policy_version_id,
            metadata={"status": "open", "action": str(analysis.action)},
        )
        self._timeline(
            incident,
            "policy_action_recorded",
            "The triggering policy action was recorded.",
            actor_type="service",
            correlation_id=correlation_id,
            referenced_event_id=event_id,
            referenced_policy_version_id=event.selected_policy_version_id,
            metadata={"action": str(analysis.action), "direction": event.direction},
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self._automatic_existing(organization_id, event_id, trigger_rule_id)
            if existing is None:
                raise IncidentPersistenceFailure("incident persistence conflict") from None
            record_security_operation("incident", "automatic_deduplicated")
            return existing
        except SQLAlchemyError as error:
            await self.db.rollback()
            raise IncidentPersistenceFailure("incident persistence failed") from error
        record_security_operation("incident", "automatic_created")
        return incident

    async def create_manual(
        self,
        actor: Membership,
        user: User,
        *,
        application_id: UUID | None,
        environment_id: UUID | None,
        title: str,
        severity: IncidentSeverity,
        safe_summary: str | None,
        idempotency_key: str | None,
    ) -> Incident:
        self.require_editor(actor)
        if environment_id is not None and application_id is None:
            raise ValidationError(details={"fields": ["application_id"]})
        await self._validate_scope(actor.organization_id, application_id, environment_id)
        try:
            cleaned_title = self._safe_operator_metadata(
                normalize_plain_text(title, maximum=200, multiline=False)
            )
            cleaned_summary = (
                self._safe_operator_metadata(normalize_plain_text(safe_summary, maximum=500))
                if safe_summary
                else f"Manually reported {severity.value} security incident."
            )
        except (ValueError, InspectionFailure) as error:
            raise ValidationError(details={"fields": ["title", "safe_summary"]}) from error
        if idempotency_key is not None and not 8 <= len(idempotency_key) <= 128:
            raise ValidationError(details={"fields": ["idempotency_key"]})
        if idempotency_key is not None:
            existing = (
                await self.db.execute(
                    select(Incident).where(
                        Incident.organization_id == actor.organization_id,
                        Incident.manual_idempotency_key == idempotency_key,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
        now = utc_now()
        incident = Incident(
            incident_id=new_uuid7(),
            organization_id=actor.organization_id,
            application_id=application_id,
            environment_id=environment_id,
            manual_idempotency_key=idempotency_key,
            status=IncidentStatus.OPEN.value,
            severity=severity.value,
            source="manual",
            title=cleaned_title,
            safe_summary=cleaned_summary,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.db.add(incident)
        self._timeline(
            incident,
            "incident_created",
            "Incident created manually.",
            actor_type="user",
            actor_user_id=user.user_id,
            correlation_id=get_request_id(),
            metadata={"status": "open", "severity": severity.value},
        )
        self._audit(incident, user.user_id, "incident.created", {"source": "manual"})
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            if idempotency_key is not None:
                existing = (
                    await self.db.execute(
                        select(Incident).where(
                            Incident.organization_id == actor.organization_id,
                            Incident.manual_idempotency_key == idempotency_key,
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    return existing
            raise ConflictError() from error
        return incident

    @staticmethod
    def _safe_operator_metadata(value: str) -> str:
        return SecurityEngine().analyze(value, Direction.INPUT).redacted_content

    async def list_incidents(
        self,
        organization_id: UUID,
        *,
        statuses: tuple[str, ...] = (),
        severities: tuple[str, ...] = (),
        application_id: UUID | None = None,
        environment_id: UUID | None = None,
        assignee_user_id: UUID | None = None,
        unassigned: bool = False,
        source: str | None = None,
        action: str | None = None,
        category: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        search: str | None = None,
        after: tuple[datetime, UUID] | None = None,
        limit: int = 50,
    ) -> tuple[list[dict[str, object]], tuple[datetime, UUID] | None]:
        conditions: list[ColumnElement[bool]] = [Incident.organization_id == organization_id]
        if statuses:
            conditions.append(Incident.status.in_(statuses))
        if severities:
            conditions.append(Incident.severity.in_(severities))
        if application_id is not None:
            conditions.append(Incident.application_id == application_id)
        if environment_id is not None:
            conditions.append(Incident.environment_id == environment_id)
        if unassigned:
            conditions.append(Incident.assignee_user_id.is_(None))
        elif assignee_user_id is not None:
            conditions.append(Incident.assignee_user_id == assignee_user_id)
        if source is not None:
            conditions.append(Incident.source == source)
        if action is not None:
            conditions.append(Incident.action == action)
        if category is not None:
            conditions.append(Incident.category == category)
        if created_from is not None:
            conditions.append(Incident.created_at >= created_from)
        if created_to is not None:
            conditions.append(Incident.created_at <= created_to)
        if search:
            literal = search.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            needle = f"%{literal}%"
            search_conditions: list[ColumnElement[bool]] = [
                func.lower(Incident.title).like(needle, escape="\\"),
                func.lower(Incident.safe_summary).like(needle, escape="\\"),
            ]
            try:
                search_conditions.append(Incident.incident_id == UUID(search))
            except ValueError:
                pass
            conditions.append(or_(*search_conditions))
        if after is not None:
            created_at, incident_id = after
            conditions.append(
                or_(
                    Incident.created_at < created_at,
                    and_(Incident.created_at == created_at, Incident.incident_id < incident_id),
                )
            )
        rows = list(
            (
                await self.db.execute(
                    select(Incident)
                    .where(*conditions)
                    .order_by(Incident.created_at.desc(), Incident.incident_id.desc())
                    .limit(limit + 1)
                )
            ).scalars()
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        names = await self._display_names(rows)
        items = [self._summary(row, names) for row in rows]
        next_key = (rows[-1].created_at, rows[-1].incident_id) if has_more and rows else None
        return items, next_key

    async def detail(self, organization_id: UUID, incident_id: UUID) -> dict[str, object]:
        incident = await self.get(organization_id, incident_id)
        names = await self._display_names([incident])
        detail = self._summary(incident, names)
        relation = list(
            (
                await self.db.execute(
                    select(IncidentSecurityEvent)
                    .where(
                        IncidentSecurityEvent.organization_id == organization_id,
                        IncidentSecurityEvent.incident_id == incident_id,
                    )
                    .order_by(IncidentSecurityEvent.created_at)
                )
            )
            .scalars()
            .all()
        )
        detail["related_analyses"] = [
            {
                "event_id": str(item.event_id),
                "analysis_id": str(item.analysis_id),
                "reason": item.reason,
            }
            for item in relation
        ]
        detail["analysis"] = await self._analysis_detail(incident, relation)
        detail["timeline"] = await self._timeline_view(organization_id, incident_id)
        detail["comments"] = await self._comments_view(organization_id, incident_id)
        return detail

    async def transition(
        self,
        actor: Membership,
        user: User,
        incident_id: UUID,
        target: IncidentStatus,
        expected_version: int,
        reason: str | None,
    ) -> Incident:
        self.require_editor(actor)
        incident = await self.get(actor.organization_id, incident_id, lock=True)
        if incident.version != expected_version:
            raise ConflictError(details={"reason": "version"})
        try:
            cleaned_reason = normalize_plain_text(reason, maximum=500) if reason else None
            validate_transition(IncidentStatus(incident.status), target, cleaned_reason)
        except ValueError as error:
            raise InvalidTransitionError() from error
        previous = incident.status
        incident.status = target.value
        incident.version += 1
        incident.updated_at = utc_now()
        if target in TERMINAL_STATUSES:
            incident.resolved_at = incident.updated_at
            incident.resolution_category = target.value
            incident.resolution_reason = cleaned_reason
        else:
            incident.resolved_at = None
            incident.resolution_category = None
            incident.resolution_reason = (
                cleaned_reason if previous in {s.value for s in TERMINAL_STATUSES} else None
            )
        event_type = (
            "false_positive_marked" if target is IncidentStatus.FALSE_POSITIVE else "status_changed"
        )
        self._timeline(
            incident,
            event_type,
            f"Incident status changed from {previous} to {target.value}.",
            actor_type="user",
            actor_user_id=user.user_id,
            correlation_id=get_request_id(),
            metadata={"from": previous, "to": target.value},
        )
        audit_action = (
            "incident.false_positive_marked"
            if target is IncidentStatus.FALSE_POSITIVE
            else "incident.status_changed"
        )
        self._audit(incident, user.user_id, audit_action, {"from": previous, "to": target.value})
        await self.db.commit()
        return incident

    async def assign(
        self,
        actor: Membership,
        user: User,
        incident_id: UUID,
        assignee_user_id: UUID | None,
        expected_version: int,
    ) -> Incident:
        self.require_editor(actor)
        incident = await self.get(actor.organization_id, incident_id, lock=True)
        if incident.version != expected_version:
            raise ConflictError(details={"reason": "version"})
        if assignee_user_id is not None:
            assignee = (
                await self.db.execute(
                    select(Membership, User)
                    .join(User, User.user_id == Membership.user_id)
                    .where(
                        Membership.organization_id == actor.organization_id,
                        Membership.user_id == assignee_user_id,
                        Membership.status == "active",
                        Membership.role.in_([role.value for role in INCIDENT_EDITORS]),
                        User.status == "active",
                    )
                )
            ).one_or_none()
            if assignee is None:
                raise NotFoundOrHiddenError()
        incident.assignee_user_id = assignee_user_id
        incident.version += 1
        incident.updated_at = utc_now()
        assigned = assignee_user_id is not None
        self._timeline(
            incident,
            "assigned" if assigned else "unassigned",
            "Incident assigned." if assigned else "Incident unassigned.",
            actor_type="user",
            actor_user_id=user.user_id,
            correlation_id=get_request_id(),
            metadata={"assignee_user_id": str(assignee_user_id) if assigned else None},
        )
        self._audit(
            incident,
            user.user_id,
            "incident.assigned" if assigned else "incident.unassigned",
            {"assignee_user_id": str(assignee_user_id) if assigned else None},
        )
        await self.db.commit()
        return incident

    async def add_comment(
        self, actor: Membership, user: User, incident_id: UUID, body: str
    ) -> IncidentComment:
        if not can_comment_on_incident(MembershipRole(actor.role)):
            raise AuthorizationError()
        incident = await self.get(actor.organization_id, incident_id)
        try:
            cleaned = normalize_plain_text(body, maximum=4000)
        except ValueError as error:
            raise ValidationError(details={"fields": ["body"]}) from error
        comment = IncidentComment(
            comment_id=new_uuid7(),
            organization_id=actor.organization_id,
            incident_id=incident.incident_id,
            author_user_id=user.user_id,
            body=cleaned,
        )
        self.db.add(comment)
        self._timeline(
            incident,
            "comment_added",
            "A comment was added.",
            actor_type="user",
            actor_user_id=user.user_id,
            correlation_id=get_request_id(),
            metadata={"comment_id": str(comment.comment_id)},
        )
        self._audit(
            incident,
            user.user_id,
            "incident.comment_added",
            {"comment_id": str(comment.comment_id)},
        )
        await self.db.commit()
        return comment

    async def assignees(self, actor: Membership) -> list[dict[str, object]]:
        self.require_editor(actor)
        rows = (
            await self.db.execute(
                select(Membership, User)
                .join(User, User.user_id == Membership.user_id)
                .where(
                    Membership.organization_id == actor.organization_id,
                    Membership.status == "active",
                    Membership.role.in_([role.value for role in INCIDENT_EDITORS]),
                    User.status == "active",
                )
                .order_by(User.normalized_email)
            )
        ).all()
        return [
            {"user_id": str(user.user_id), "email": user.email, "role": membership.role}
            for membership, user in rows
        ]

    async def get(
        self, organization_id: UUID, incident_id: UUID, *, lock: bool = False
    ) -> Incident:
        query = select(Incident).where(
            Incident.organization_id == organization_id, Incident.incident_id == incident_id
        )
        if lock:
            query = query.with_for_update()
        incident = (await self.db.execute(query)).scalar_one_or_none()
        if incident is None:
            raise NotFoundOrHiddenError()
        return incident

    @staticmethod
    def require_editor(actor: Membership) -> None:
        if not can_edit_incident(MembershipRole(actor.role)):
            raise AuthorizationError()

    async def _validate_scope(
        self, organization_id: UUID, application_id: UUID | None, environment_id: UUID | None
    ) -> None:
        if application_id is None:
            return
        application = (
            await self.db.execute(
                select(Application).where(
                    Application.organization_id == organization_id,
                    Application.application_id == application_id,
                )
            )
        ).scalar_one_or_none()
        if application is None:
            raise NotFoundOrHiddenError()
        if environment_id is not None:
            environment = (
                await self.db.execute(
                    select(Environment).where(
                        Environment.organization_id == organization_id,
                        Environment.application_id == application_id,
                        Environment.environment_id == environment_id,
                    )
                )
            ).scalar_one_or_none()
            if environment is None:
                raise NotFoundOrHiddenError()

    async def _primary_finding(self, analysis_id: UUID) -> Finding | None:
        findings = list(
            (
                await self.db.execute(select(Finding).where(Finding.analysis_id == analysis_id))
            ).scalars()
        )
        return max(
            findings,
            key=lambda row: (SEVERITY_RANK.get(row.severity, 0), row.confidence, row.category),
            default=None,
        )

    async def _automatic_existing(
        self, organization_id: UUID, event_id: UUID, trigger_rule_id: str
    ) -> Incident | None:
        return (
            await self.db.execute(
                select(Incident).where(
                    Incident.organization_id == organization_id,
                    Incident.primary_event_id == event_id,
                    Incident.trigger_rule_id == trigger_rule_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def _trigger_rule(event: SecurityEvent, analysis: AnalysisResult) -> str:
        policy = (
            str(event.selected_policy_version_id) if event.selected_policy_version_id else "none"
        )
        return f"gateway:{event.direction}:{analysis.action}:{policy}"

    async def _display_names(self, incidents: list[Incident]) -> dict[str, dict[UUID, str]]:
        application_ids = {row.application_id for row in incidents if row.application_id}
        environment_ids = {row.environment_id for row in incidents if row.environment_id}
        user_ids = {row.assignee_user_id for row in incidents if row.assignee_user_id}
        applications = (
            list(
                (
                    await self.db.execute(
                        select(Application).where(Application.application_id.in_(application_ids))
                    )
                ).scalars()
            )
            if application_ids
            else []
        )
        environments = (
            list(
                (
                    await self.db.execute(
                        select(Environment).where(Environment.environment_id.in_(environment_ids))
                    )
                ).scalars()
            )
            if environment_ids
            else []
        )
        users = (
            list((await self.db.execute(select(User).where(User.user_id.in_(user_ids)))).scalars())
            if user_ids
            else []
        )
        return {
            "applications": {row.application_id: row.name for row in applications},
            "environments": {row.environment_id: row.type for row in environments},
            "users": {row.user_id: row.email for row in users},
        }

    @staticmethod
    def _summary(incident: Incident, names: dict[str, dict[UUID, str]]) -> dict[str, object]:
        return {
            "incident_id": str(incident.incident_id),
            "organization_id": str(incident.organization_id),
            "application_id": str(incident.application_id) if incident.application_id else None,
            "application_name": (
                names["applications"].get(incident.application_id)
                if incident.application_id
                else None
            ),
            "environment_id": str(incident.environment_id) if incident.environment_id else None,
            "environment_name": (
                names["environments"].get(incident.environment_id)
                if incident.environment_id
                else None
            ),
            "primary_event_id": str(incident.primary_event_id)
            if incident.primary_event_id
            else None,
            "primary_analysis_id": str(incident.primary_analysis_id)
            if incident.primary_analysis_id
            else None,
            "status": incident.status,
            "severity": incident.severity,
            "risk_score": incident.risk_score,
            "category": incident.category,
            "detector_id": incident.detector_id,
            "action": incident.action,
            "source": incident.source,
            "direction": incident.direction,
            "title": incident.title,
            "safe_summary": incident.safe_summary,
            "assignee_user_id": str(incident.assignee_user_id)
            if incident.assignee_user_id
            else None,
            "assignee_email": (
                names["users"].get(incident.assignee_user_id) if incident.assignee_user_id else None
            ),
            "resolution_category": incident.resolution_category,
            "resolution_reason": incident.resolution_reason,
            "privacy_mode": incident.privacy_mode,
            "security_retention_days": incident.security_retention_days,
            "version": incident.version,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat(),
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        }

    async def _analysis_detail(
        self, incident: Incident, relations: list[IncidentSecurityEvent]
    ) -> dict[str, object] | None:
        if incident.primary_analysis_id is None:
            return None
        relation = next(
            (row for row in relations if row.analysis_id == incident.primary_analysis_id), None
        )
        if relation is None:
            return {"state": "content_no_longer_retained"}
        row = (
            await self.db.execute(
                select(SecurityEvent, AnalysisResult)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .where(
                    SecurityEvent.organization_id == incident.organization_id,
                    AnalysisResult.analysis_id == incident.primary_analysis_id,
                )
            )
        ).one_or_none()
        if row is None:
            return {"state": "content_no_longer_retained"}
        event, analysis = row
        findings = list(
            (
                await self.db.execute(
                    select(Finding)
                    .where(Finding.analysis_id == analysis.analysis_id)
                    .order_by(Finding.category, Finding.finding_id)
                )
            ).scalars()
        )
        decision = (
            await self.db.execute(
                select(PolicyDecision).where(PolicyDecision.analysis_id == analysis.analysis_id)
            )
        ).scalar_one_or_none()
        result: dict[str, object] = {
            "state": "available",
            "analysis_id": str(analysis.analysis_id),
            "event_id": str(event.event_id),
            "privacy_mode": event.privacy_mode,
            "risk_score": analysis.risk_score,
            "severity": analysis.risk_severity,
            "confidence": analysis.risk_confidence,
            "risk_explanation": {
                "base_score": analysis.base_score,
                "corroboration_bonus": analysis.corroboration_bonus,
                "critical_floor": analysis.critical_floor,
                "profile_version": analysis.risk_profile_version,
            },
            "findings": [
                {
                    "finding_id": str(item.finding_id),
                    "detector_id": item.detector_id,
                    "detector_version": item.detector_version,
                    "category": item.category,
                    "severity": item.severity,
                    "confidence": item.confidence,
                    "evidence": item.evidence,
                    "safe_explanation": item.safe_explanation,
                }
                for item in findings
            ],
            "policy_decision": (
                {
                    "policy_decision_id": str(decision.policy_decision_id),
                    "action": decision.action,
                    "selected_policy_id": str(decision.selected_policy_id)
                    if decision.selected_policy_id
                    else None,
                    "selected_policy_version_id": str(decision.selected_policy_version_id)
                    if decision.selected_policy_version_id
                    else None,
                    "rationale_code": decision.rationale_code,
                }
                if decision is not None
                else None
            ),
        }
        if event.content is not None:
            result["content"] = event.content
        else:
            result["content_state"] = "not_retained"
        return result

    async def _timeline_view(
        self, organization_id: UUID, incident_id: UUID
    ) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                select(IncidentTimelineEvent, User)
                .outerjoin(User, User.user_id == IncidentTimelineEvent.actor_user_id)
                .where(
                    IncidentTimelineEvent.organization_id == organization_id,
                    IncidentTimelineEvent.incident_id == incident_id,
                )
                .order_by(IncidentTimelineEvent.created_at, IncidentTimelineEvent.timeline_event_id)
            )
        ).all()
        return [
            {
                "timeline_event_id": str(event.timeline_event_id),
                "event_type": event.event_type,
                "actor_type": event.actor_type,
                "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                "actor_email": user.email if user is not None else None,
                "safe_summary": event.safe_summary,
                "safe_metadata": event.safe_metadata,
                "created_at": event.created_at.isoformat(),
            }
            for event, user in rows
        ]

    async def _comments_view(
        self, organization_id: UUID, incident_id: UUID
    ) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                select(IncidentComment, User)
                .join(User, User.user_id == IncidentComment.author_user_id)
                .where(
                    IncidentComment.organization_id == organization_id,
                    IncidentComment.incident_id == incident_id,
                )
                .order_by(IncidentComment.created_at, IncidentComment.comment_id)
            )
        ).all()
        return [self.comment_view(comment, user) for comment, user in rows]

    @staticmethod
    def comment_view(comment: IncidentComment, user: User) -> dict[str, object]:
        return {
            "comment_id": str(comment.comment_id),
            "incident_id": str(comment.incident_id),
            "author_user_id": str(comment.author_user_id),
            "author_email": user.email,
            "body": comment.body,
            "created_at": comment.created_at.isoformat(),
        }

    def _timeline(
        self,
        incident: Incident,
        event_type: str,
        safe_summary: str,
        *,
        actor_type: str,
        actor_user_id: UUID | None = None,
        correlation_id: str | None = None,
        referenced_event_id: UUID | None = None,
        referenced_policy_version_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            IncidentTimelineEvent(
                organization_id=incident.organization_id,
                incident_id=incident.incident_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_user_id=actor_user_id,
                safe_summary=safe_summary,
                safe_metadata=metadata or {},
                correlation_id=correlation_id,
                referenced_event_id=referenced_event_id,
                referenced_policy_version_id=referenced_policy_version_id,
            )
        )

    def _audit(
        self,
        incident: Incident,
        actor_user_id: UUID,
        action: str,
        metadata: dict[str, object],
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=incident.organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="incident",
                resource_id=str(incident.incident_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata=metadata,
            )
        )
