"""Tenant-scoped, privacy-safe operational dashboard aggregation."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter_ns
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from renzai.core.errors import NotFoundOrHiddenError, ValidationError
from renzai.core.time import utc_now
from renzai.modules.analytics.domain import (
    ActivityBucket,
    AnalyticsSource,
    AnalyticsWindow,
    DashboardSummary,
    WindowRange,
    window_range,
)
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.incidents.models import Incident
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent

RISK_LEVELS = ("low", "medium", "high", "critical")
ACTIONS = ("allow", "flag", "redact", "require_review", "block")
INCIDENT_STATUSES = ("open", "investigating", "resolved", "ignored", "false_positive")
TOP_LIMIT = 10
PROVIDER_LIMIT = 20


class AnalyticsService:
    def __init__(self, db: AsyncSession, *, as_of: datetime | None = None) -> None:
        self.db = db
        self.as_of = as_of or utc_now()

    async def dashboard(
        self,
        organization_id: UUID,
        *,
        window: AnalyticsWindow,
        application_id: UUID | None = None,
        environment_id: UUID | None = None,
        source: AnalyticsSource | None = None,
    ) -> dict[str, object]:
        started = perf_counter_ns()
        await self._validate_scope(organization_id, application_id, environment_id)
        selected = window_range(window, self.as_of)
        summary = await self._summary(
            organization_id, selected, application_id, environment_id, source
        )
        activity = await self._activity(
            organization_id, selected, application_id, environment_id, source
        )
        risk = await self._risk_distribution(
            organization_id, selected, application_id, environment_id, source
        )
        threats = await self._threats(
            organization_id, selected, application_id, environment_id, source
        )
        detectors = await self._detectors(
            organization_id, selected, application_id, environment_id, source
        )
        actions = await self._actions(
            organization_id, selected, application_id, environment_id, source
        )
        applications = await self._application_breakdown(
            organization_id, selected, application_id, environment_id, source
        )
        environments = await self._environment_breakdown(
            organization_id, selected, application_id, environment_id, source
        )
        providers = await self._providers(
            organization_id, selected, application_id, environment_id, source
        )
        incidents = await self._incidents(
            organization_id, selected, application_id, environment_id, source
        )
        recent = await self._recent_incidents(
            organization_id, selected, application_id, environment_id, source
        )
        return {
            "filters": {
                "window": window.value,
                "window_start": selected.start.isoformat(),
                "window_end": selected.end.isoformat(),
                "bucket": selected.bucket,
                "application_id": str(application_id) if application_id else None,
                "environment_id": str(environment_id) if environment_id else None,
                "source": source.value if source else None,
            },
            "summary": summary.serialize(),
            "activity": [item.serialize() for item in activity],
            "risk_distribution": risk,
            "threat_categories": threats,
            "top_detectors": detectors,
            "policy_actions": actions,
            "applications": applications,
            "environments": environments,
            "providers": providers,
            "incidents": incidents,
            "recent_incidents": recent,
            "query_duration_ms": (perf_counter_ns() - started) // 1_000_000,
        }

    async def _validate_scope(
        self,
        organization_id: UUID,
        application_id: UUID | None,
        environment_id: UUID | None,
    ) -> None:
        if environment_id is not None and application_id is None:
            raise ValidationError(details={"fields": ["application_id", "environment_id"]})
        if application_id is None:
            return
        application = await self.db.scalar(
            select(Application.application_id).where(
                Application.organization_id == organization_id,
                Application.application_id == application_id,
            )
        )
        if application is None:
            raise NotFoundOrHiddenError()
        if environment_id is not None:
            environment = await self.db.scalar(
                select(Environment.environment_id).where(
                    Environment.organization_id == organization_id,
                    Environment.application_id == application_id,
                    Environment.environment_id == environment_id,
                )
            )
            if environment is None:
                raise NotFoundOrHiddenError()

    def _analysis_conditions(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            SecurityEvent.organization_id == organization_id,
            SecurityEvent.occurred_at >= selected.start,
            SecurityEvent.occurred_at <= selected.end,
            AnalysisResult.status == "completed",
        ]
        if application_id is not None:
            conditions.append(SecurityEvent.application_id == application_id)
        if environment_id is not None:
            conditions.append(SecurityEvent.environment_id == environment_id)
        if source is not None:
            conditions.append(SecurityEvent.source == source.value)
        return conditions

    def _incident_conditions(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            Incident.organization_id == organization_id,
            Incident.created_at >= selected.start,
            Incident.created_at <= selected.end,
        ]
        if application_id is not None:
            conditions.append(Incident.application_id == application_id)
        if environment_id is not None:
            conditions.append(Incident.environment_id == environment_id)
        if source is not None:
            conditions.append(Incident.source == source.value)
        return conditions

    def _gateway_conditions(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            GatewayProviderCall.organization_id == organization_id,
            GatewayProviderCall.created_at >= selected.start,
            GatewayProviderCall.created_at <= selected.end,
        ]
        if application_id is not None:
            conditions.append(GatewayProviderCall.application_id == application_id)
        if environment_id is not None:
            conditions.append(GatewayProviderCall.environment_id == environment_id)
        return conditions

    async def _summary(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> DashboardSummary:
        conditions = self._analysis_conditions(
            organization_id, selected, application_id, environment_id, source
        )
        row = (
            await self.db.execute(
                select(
                    func.count(AnalysisResult.analysis_id),
                    func.coalesce(
                        func.sum(case((AnalysisResult.finding_count > 0, 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "block", 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "require_review", 1), else_=0)),
                        0,
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "redact", 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.risk_severity == "critical", 1), else_=0)),
                        0,
                    ),
                )
                .select_from(SecurityEvent)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .where(*conditions)
            )
        ).one()
        analyses, threats, blocked, review, redacted, critical = (int(value) for value in row)
        gateway_requests = 0
        if source in (None, AnalyticsSource.GATEWAY):
            gateway_requests = int(
                await self.db.scalar(
                    select(func.count(GatewayProviderCall.gateway_call_id)).where(
                        *self._gateway_conditions(
                            organization_id, selected, application_id, environment_id
                        )
                    )
                )
                or 0
            )
        open_incidents = int(
            await self.db.scalar(
                select(func.count(Incident.incident_id)).where(
                    *self._incident_conditions(
                        organization_id, selected, application_id, environment_id, source
                    ),
                    Incident.status == "open",
                )
            )
            or 0
        )
        return DashboardSummary(
            analyses=analyses,
            gateway_requests=gateway_requests,
            threats_detected=threats,
            blocked=blocked,
            require_review=review,
            redacted=redacted,
            critical_analyses=critical,
            open_incidents=open_incidents,
            threat_rate_numerator=threats,
            threat_rate_denominator=analyses,
            threat_rate_percent=round((threats / analyses) * 100, 2) if analyses else 0.0,
        )

    async def _activity(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[ActivityBucket]:
        dialect = self.db.get_bind().dialect.name
        if dialect == "postgresql":
            bucket_expression = func.date_trunc(
                selected.bucket, func.timezone("UTC", SecurityEvent.occurred_at)
            )
        else:
            pattern = (
                "%Y-%m-%dT%H:00:00+00:00"
                if selected.bucket == "hour"
                else "%Y-%m-%dT00:00:00+00:00"
            )
            bucket_expression = func.strftime(pattern, SecurityEvent.occurred_at)
        rows = (
            await self.db.execute(
                select(
                    bucket_expression.label("bucket_start"),
                    func.count(AnalysisResult.analysis_id),
                    func.coalesce(
                        func.sum(case((AnalysisResult.finding_count > 0, 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "block", 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "require_review", 1), else_=0)),
                        0,
                    ),
                )
                .select_from(SecurityEvent)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .where(
                    *self._analysis_conditions(
                        organization_id, selected, application_id, environment_id, source
                    )
                )
                .group_by(bucket_expression)
                .order_by(bucket_expression)
            )
        ).all()
        counts: dict[datetime, tuple[int, int, int, int]] = {}
        for raw_bucket, analyses, threats, blocked, review in rows:
            if isinstance(raw_bucket, str):
                parsed = datetime.fromisoformat(raw_bucket)
            else:
                parsed = raw_bucket.replace(tzinfo=UTC) if raw_bucket.tzinfo is None else raw_bucket
            counts[parsed.astimezone(UTC)] = (
                int(analyses),
                int(threats),
                int(blocked),
                int(review),
            )
        return [
            ActivityBucket(bucket_start, *counts.get(bucket_start, (0, 0, 0, 0)))
            for bucket_start in selected.bucket_starts
        ]

    async def _risk_distribution(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        rows = await self._analysis_group(
            AnalysisResult.risk_severity,
            organization_id,
            selected,
            application_id,
            environment_id,
            source,
        )
        counts = {str(key): int(value) for key, value in rows if key is not None}
        return [{"severity": level, "count": counts.get(level, 0)} for level in RISK_LEVELS]

    async def _actions(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        rows = await self._analysis_group(
            AnalysisResult.action,
            organization_id,
            selected,
            application_id,
            environment_id,
            source,
        )
        counts = {str(key): int(value) for key, value in rows if key is not None}
        return [{"action": action, "count": counts.get(action, 0)} for action in ACTIONS]

    async def _analysis_group(
        self,
        column: Any,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[Any]:
        return list(
            (
                await self.db.execute(
                    select(column, func.count(AnalysisResult.analysis_id))
                    .select_from(SecurityEvent)
                    .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                    .where(
                        *self._analysis_conditions(
                            organization_id, selected, application_id, environment_id, source
                        )
                    )
                    .group_by(column)
                )
            ).all()
        )

    async def _threats(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        count_label = func.count(Finding.finding_id).label("finding_count")
        rows = (
            await self.db.execute(
                select(
                    Finding.category,
                    count_label,
                    func.count(distinct(Finding.analysis_id)).label("affected_analyses"),
                )
                .select_from(Finding)
                .join(AnalysisResult, AnalysisResult.analysis_id == Finding.analysis_id)
                .join(SecurityEvent, SecurityEvent.event_id == AnalysisResult.event_id)
                .where(
                    *self._analysis_conditions(
                        organization_id, selected, application_id, environment_id, source
                    )
                )
                .group_by(Finding.category)
                .order_by(count_label.desc(), Finding.category.asc())
                .limit(TOP_LIMIT)
            )
        ).all()
        return [
            {
                "category": category,
                "finding_count": int(finding_count),
                "affected_analyses": int(affected),
            }
            for category, finding_count, affected in rows
        ]

    async def _detectors(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        count_label = func.count(Finding.finding_id).label("finding_count")
        rows = (
            await self.db.execute(
                select(
                    Finding.detector_id,
                    Finding.detector_version,
                    count_label,
                    func.count(distinct(Finding.analysis_id)),
                    func.avg(Finding.confidence),
                )
                .select_from(Finding)
                .join(AnalysisResult, AnalysisResult.analysis_id == Finding.analysis_id)
                .join(SecurityEvent, SecurityEvent.event_id == AnalysisResult.event_id)
                .where(
                    *self._analysis_conditions(
                        organization_id, selected, application_id, environment_id, source
                    )
                )
                .group_by(Finding.detector_id, Finding.detector_version)
                .order_by(
                    count_label.desc(), Finding.detector_id.asc(), Finding.detector_version.asc()
                )
                .limit(TOP_LIMIT)
            )
        ).all()
        return [
            {
                "detector_id": detector_id,
                "detector_version": version,
                "finding_count": int(finding_count),
                "affected_analyses": int(affected),
                "average_confidence": round(float(average), 2),
            }
            for detector_id, version, finding_count, affected, average in rows
        ]

    async def _application_breakdown(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        conditions = self._analysis_conditions(
            organization_id, selected, application_id, environment_id, source
        )
        rows = (
            await self.db.execute(
                select(
                    Application.application_id,
                    Application.name,
                    func.count(AnalysisResult.analysis_id).label("analyses"),
                    func.coalesce(
                        func.sum(case((AnalysisResult.finding_count > 0, 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.risk_severity == "critical", 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "block", 1), else_=0)), 0
                    ),
                )
                .select_from(SecurityEvent)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .join(Application, Application.application_id == SecurityEvent.application_id)
                .where(*conditions)
                .group_by(Application.application_id, Application.name)
                .order_by(
                    func.count(AnalysisResult.analysis_id).desc(), Application.application_id.asc()
                )
                .limit(TOP_LIMIT)
            )
        ).all()
        incident_counts = await self._incident_counts_by(
            Incident.application_id,
            organization_id,
            selected,
            application_id,
            environment_id,
            source,
        )
        return [
            {
                "application_id": str(app_id),
                "application_name": name,
                "analysis_count": int(analyses),
                "threat_count": int(threats),
                "critical_count": int(critical),
                "blocked_count": int(blocked),
                "incident_count": incident_counts.get(app_id, 0),
            }
            for app_id, name, analyses, threats, critical, blocked in rows
        ]

    async def _environment_breakdown(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                select(
                    Environment.environment_id,
                    Environment.type,
                    func.count(AnalysisResult.analysis_id),
                    func.coalesce(
                        func.sum(case((AnalysisResult.finding_count > 0, 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(case((AnalysisResult.action == "block", 1), else_=0)), 0
                    ),
                )
                .select_from(SecurityEvent)
                .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
                .join(Environment, Environment.environment_id == SecurityEvent.environment_id)
                .where(
                    *self._analysis_conditions(
                        organization_id, selected, application_id, environment_id, source
                    )
                )
                .group_by(Environment.environment_id, Environment.type)
                .order_by(
                    func.count(AnalysisResult.analysis_id).desc(), Environment.environment_id.asc()
                )
                .limit(TOP_LIMIT)
            )
        ).all()
        incident_counts = await self._incident_counts_by(
            Incident.environment_id,
            organization_id,
            selected,
            application_id,
            environment_id,
            source,
        )
        return [
            {
                "environment_id": str(env_id),
                "environment_type": env_type,
                "analysis_count": int(analyses),
                "threat_count": int(threats),
                "blocked_count": int(blocked),
                "incident_count": incident_counts.get(env_id, 0),
            }
            for env_id, env_type, analyses, threats, blocked in rows
        ]

    async def _incident_counts_by(
        self,
        column: Any,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> dict[UUID, int]:
        rows = (
            await self.db.execute(
                select(column, func.count(Incident.incident_id))
                .where(
                    *self._incident_conditions(
                        organization_id, selected, application_id, environment_id, source
                    ),
                    column.is_not(None),
                )
                .group_by(column)
            )
        ).all()
        return {identifier: int(count) for identifier, count in rows}

    async def _providers(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        if source not in (None, AnalyticsSource.GATEWAY):
            return []
        request_count = func.count(GatewayProviderCall.gateway_call_id).label("request_count")
        rows = (
            await self.db.execute(
                select(
                    GatewayProviderCall.provider_id,
                    ProviderConfiguration.name,
                    GatewayProviderCall.configured_model,
                    request_count,
                    *[
                        func.coalesce(
                            func.sum(case((GatewayProviderCall.outcome == outcome, 1), else_=0)), 0
                        )
                        for outcome in (
                            "completed",
                            "provider_timeout",
                            "provider_error",
                            "configuration_error",
                            "output_block",
                            "output_review",
                            "output_inspection_failure",
                        )
                    ],
                    func.avg(GatewayProviderCall.provider_latency_ms),
                )
                .select_from(GatewayProviderCall)
                .join(
                    ProviderConfiguration,
                    ProviderConfiguration.provider_id == GatewayProviderCall.provider_id,
                )
                .where(
                    *self._gateway_conditions(
                        organization_id, selected, application_id, environment_id
                    )
                )
                .group_by(
                    GatewayProviderCall.provider_id,
                    ProviderConfiguration.name,
                    GatewayProviderCall.configured_model,
                )
                .order_by(
                    request_count.desc(),
                    GatewayProviderCall.provider_id.asc(),
                    GatewayProviderCall.configured_model.asc(),
                )
                .limit(PROVIDER_LIMIT)
            )
        ).all()
        keys = (
            "completed",
            "provider_timeout",
            "provider_error",
            "configuration_error",
            "output_block",
            "output_review",
            "output_inspection_failure",
        )
        output: list[dict[str, object]] = []
        for row in rows:
            item: dict[str, object] = {
                "provider_id": str(row[0]),
                "provider_name": row[1],
                "configured_model": row[2],
                "request_count": int(row[3]),
            }
            item.update({key: int(row[4 + index]) for index, key in enumerate(keys)})
            item["average_latency_ms"] = round(float(row[-1]), 2)
            output.append(item)
        return output

    async def _incidents(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> dict[str, object]:
        conditions = self._incident_conditions(
            organization_id, selected, application_id, environment_id, source
        )
        rows = (
            await self.db.execute(
                select(Incident.status, func.count(Incident.incident_id))
                .where(*conditions)
                .group_by(Incident.status)
            )
        ).all()
        counts = {status: int(count) for status, count in rows}
        critical_open, unassigned_open = (
            int(value)
            for value in (
                await self.db.execute(
                    select(
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        and_(
                                            Incident.status == "open",
                                            Incident.severity == "critical",
                                        ),
                                        1,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                        func.coalesce(
                            func.sum(
                                case(
                                    (
                                        and_(
                                            Incident.status == "open",
                                            Incident.assignee_user_id.is_(None),
                                        ),
                                        1,
                                    ),
                                    else_=0,
                                )
                            ),
                            0,
                        ),
                    ).where(*conditions)
                )
            ).one()
        )
        return {
            "statuses": [
                {"status": status, "count": counts.get(status, 0)} for status in INCIDENT_STATUSES
            ],
            "critical_open": critical_open,
            "unassigned_open": unassigned_open,
        }

    async def _recent_incidents(
        self,
        organization_id: UUID,
        selected: WindowRange,
        application_id: UUID | None,
        environment_id: UUID | None,
        source: AnalyticsSource | None,
    ) -> list[dict[str, object]]:
        rows = (
            await self.db.execute(
                select(
                    Incident.incident_id,
                    Incident.status,
                    Incident.severity,
                    Incident.category,
                    Incident.action,
                    Incident.application_id,
                    Incident.environment_id,
                    Incident.created_at,
                )
                .where(
                    *self._incident_conditions(
                        organization_id, selected, application_id, environment_id, source
                    )
                )
                .order_by(Incident.created_at.desc(), Incident.incident_id.desc())
                .limit(5)
            )
        ).all()
        return [
            {
                "incident_id": str(row.incident_id),
                "status": row.status,
                "severity": row.severity,
                "category": row.category,
                "action": row.action,
                "application_id": str(row.application_id) if row.application_id else None,
                "environment_id": str(row.environment_id) if row.environment_id else None,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
