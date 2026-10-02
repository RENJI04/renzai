"""Tenant-scoped incident, relation, comment, and timeline persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            name="fk_incidents_application_tenant",
        ),
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            name="fk_incidents_environment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assignee_user_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_incidents_assignee_membership",
        ),
        UniqueConstraint("incident_id", "organization_id", name="uq_incidents_id_organization"),
        UniqueConstraint(
            "organization_id",
            "primary_event_id",
            "trigger_rule_id",
            name="uq_incidents_automatic_identity",
        ),
        UniqueConstraint(
            "organization_id", "manual_idempotency_key", name="uq_incidents_manual_idempotency"
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'ignored', 'false_positive')",
            name="ck_incidents_status",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_incidents_severity",
        ),
        CheckConstraint(
            "risk_score IS NULL OR risk_score BETWEEN 0 AND 100", name="ck_incidents_risk"
        ),
        CheckConstraint(
            "action IS NULL OR action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_incidents_action",
        ),
        CheckConstraint(
            "source IN ('manual', 'gateway', 'analyze', 'playground')",
            name="ck_incidents_source",
        ),
        CheckConstraint(
            "(primary_event_id IS NULL AND primary_analysis_id IS NULL "
            "AND trigger_rule_id IS NULL) "
            "OR (primary_event_id IS NOT NULL AND primary_analysis_id IS NOT NULL "
            "AND trigger_rule_id IS NOT NULL)",
            name="ck_incidents_trigger_shape",
        ),
        CheckConstraint(
            "environment_id IS NULL OR application_id IS NOT NULL",
            name="ck_incidents_environment_scope",
        ),
        CheckConstraint("version >= 1", name="ck_incidents_version"),
        Index("ix_incidents_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_incidents_org_created", "organization_id", "created_at"),
        Index("ix_incidents_org_severity_created", "organization_id", "severity", "created_at"),
        Index(
            "ix_incidents_org_assignee_created", "organization_id", "assignee_user_id", "created_at"
        ),
        Index(
            "ix_incidents_scope_created",
            "organization_id",
            "application_id",
            "environment_id",
            "created_at",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id"), index=True
    )
    application_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    primary_event_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    primary_analysis_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    trigger_rule_id: Mapped[str | None] = mapped_column(String(160))
    manual_idempotency_key: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    detector_id: Mapped[str | None] = mapped_column(String(96))
    action: Mapped[str | None] = mapped_column(String(24), index=True)
    source: Mapped[str] = mapped_column(String(24), index=True)
    direction: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    safe_summary: Mapped[str] = mapped_column(String(500))
    assignee_user_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    resolution_category: Mapped[str | None] = mapped_column(String(32))
    resolution_reason: Mapped[str | None] = mapped_column(String(500))
    privacy_mode: Mapped[str | None] = mapped_column(String(32))
    security_retention_days: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentSecurityEvent(Base):
    __tablename__ = "incident_security_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_events_incident_tenant",
        ),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["security_events.event_id", "security_events.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_events_event_tenant",
        ),
        ForeignKeyConstraint(
            ["analysis_id", "event_id"],
            ["analysis_results.analysis_id", "analysis_results.event_id"],
            ondelete="CASCADE",
            name="fk_incident_events_analysis_event",
        ),
        UniqueConstraint("incident_id", "analysis_id", name="uq_incident_events_analysis"),
    )

    relation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    incident_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    event_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    analysis_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    reason: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IncidentComment(Base):
    __tablename__ = "incident_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_comments_incident_tenant",
        ),
        CheckConstraint("length(body) BETWEEN 1 AND 4000", name="ck_incident_comments_body"),
        Index("ix_incident_comments_incident_created", "incident_id", "created_at"),
    )

    comment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    incident_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    author_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.user_id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_timeline_incident_tenant",
        ),
        CheckConstraint(
            "event_type IN ('incident_created', 'status_changed', 'assigned', 'unassigned', "
            "'comment_added', 'false_positive_marked', 'related_event_added', "
            "'policy_action_recorded')",
            name="ck_incident_timeline_type",
        ),
        CheckConstraint("actor_type IN ('user', 'service')", name="ck_incident_timeline_actor"),
        Index("ix_incident_timeline_incident_created", "incident_id", "created_at"),
    )

    timeline_event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    incident_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.user_id"))
    safe_summary: Mapped[str] = mapped_column(String(500))
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    referenced_event_id: Mapped[UUID | None] = mapped_column(Uuid)
    referenced_policy_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
