"""Privacy-filtered analysis persistence."""

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


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_security_events_environment_tenant",
        ),
        CheckConstraint("direction IN ('input', 'output')", name="ck_security_events_direction"),
        CheckConstraint(
            "source IN ('analyze', 'playground', 'gateway')",
            name="ck_security_events_source",
        ),
        CheckConstraint(
            "action IS NULL OR action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_security_events_action",
        ),
        CheckConstraint(
            "risk_score IS NULL OR risk_score BETWEEN 0 AND 100",
            name="ck_security_events_risk_score",
        ),
        UniqueConstraint("event_id", "organization_id", name="uq_security_events_id_organization"),
        Index(
            "ix_security_events_scope_time",
            "organization_id",
            "application_id",
            "environment_id",
            "occurred_at",
        ),
        Index("ix_security_events_org_time", "organization_id", "occurred_at"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(24), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    privacy_mode: Mapped[str] = mapped_column(String(32))
    content: Mapped[str | None] = mapped_column(Text)
    content_bytes: Mapped[int] = mapped_column(Integer)
    retention_days: Mapped[int] = mapped_column(Integer)
    action: Mapped[str | None] = mapped_column(String(24), index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_severity: Mapped[str | None] = mapped_column(String(16), index=True)
    risk_profile_id: Mapped[UUID | None] = mapped_column(Uuid)
    risk_profile_version: Mapped[int | None] = mapped_column(Integer)
    selected_policy_id: Mapped[UUID | None] = mapped_column(Uuid)
    selected_policy_version_id: Mapped[UUID | None] = mapped_column(Uuid)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_analysis_results_risk_score"),
        CheckConstraint(
            "risk_confidence BETWEEN 0 AND 100",
            name="ck_analysis_results_risk_confidence",
        ),
        CheckConstraint(
            "risk_severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_analysis_results_risk_severity",
        ),
        CheckConstraint(
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_analysis_results_action",
        ),
        UniqueConstraint("analysis_id", "event_id", name="uq_analysis_results_id_event"),
    )

    analysis_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("security_events.event_id", ondelete="CASCADE"), unique=True, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    normalization_version: Mapped[str] = mapped_column(String(32))
    ruleset_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    finding_count: Mapped[int] = mapped_column(Integer)
    normalization_ms: Mapped[int] = mapped_column(Integer)
    detector_ms: Mapped[int] = mapped_column(Integer)
    total_ms: Mapped[int] = mapped_column(Integer)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON)
    risk_profile_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("risk_profiles.risk_profile_id")
    )
    risk_profile_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "risk_profile_versions.risk_profile_version_id",
            name="fk_analysis_results_risk_profile_version",
        ),
    )
    risk_profile_version: Mapped[int | None] = mapped_column(Integer)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_severity: Mapped[str | None] = mapped_column(String(16))
    risk_confidence: Mapped[int | None] = mapped_column(Integer)
    base_score: Mapped[int | None] = mapped_column(Integer)
    corroboration_bonus: Mapped[int | None] = mapped_column(Integer)
    critical_floor: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str | None] = mapped_column(String(24))
    risk_ms: Mapped[int | None] = mapped_column(Integer)
    policy_ms: Mapped[int | None] = mapped_column(Integer)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_findings_confidence"),
        Index("ix_findings_analysis_category", "analysis_id", "category"),
        Index("ix_findings_detector", "detector_id"),
    )

    finding_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_results.analysis_id", ondelete="CASCADE"), index=True
    )
    detector_id: Mapped[str] = mapped_column(String(96))
    detector_version: Mapped[str] = mapped_column(String(32))
    ruleset_version: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[int] = mapped_column(Integer)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    safe_explanation: Mapped[str] = mapped_column(String(320))
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    overlap_group: Mapped[str | None] = mapped_column(String(64))
