"""Tenant-scoped, immutable-version policy persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('organization', 'application', 'environment')",
            name="ck_policies_scope_kind",
        ),
        CheckConstraint("phase IN ('input', 'output')", name="ck_policies_phase"),
        CheckConstraint("priority >= 1", name="ck_policies_priority"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_policies_status"),
        CheckConstraint(
            "(scope_kind = 'organization' AND scope_id = organization_id "
            "AND application_id IS NULL AND environment_id IS NULL) OR "
            "(scope_kind = 'application' AND scope_id = application_id "
            "AND application_id IS NOT NULL AND environment_id IS NULL) OR "
            "(scope_kind = 'environment' AND scope_id = environment_id "
            "AND application_id IS NOT NULL AND environment_id IS NOT NULL)",
            name="ck_policies_scope_shape",
        ),
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            ondelete="CASCADE",
            name="fk_policies_application_tenant",
        ),
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_policies_environment_tenant",
        ),
        UniqueConstraint("policy_id", "organization_id", name="uq_policies_id_organization"),
        UniqueConstraint(
            "application_id", "baseline_key", name="uq_policies_application_baseline_key"
        ),
        Index(
            "uq_policies_effective_priority",
            "organization_id",
            "scope_kind",
            "scope_id",
            "phase",
            "priority",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
            sqlite_where=text("archived_at IS NULL"),
        ),
        Index(
            "ix_policies_evaluation",
            "organization_id",
            "scope_kind",
            "scope_id",
            "phase",
            "enabled",
            "priority",
        ),
    )

    policy_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    scope_kind: Mapped[str] = mapped_column(String(24))
    scope_id: Mapped[UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(120))
    phase: Mapped[str] = mapped_column(String(16))
    priority: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    active_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="active")
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_key: Mapped[str | None] = mapped_column(String(96))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "organization_id"],
            ["policies.policy_id", "policies.organization_id"],
            ondelete="CASCADE",
            name="fk_policy_versions_policy_tenant",
        ),
        UniqueConstraint("policy_id", "version", name="uq_policy_versions_number"),
        CheckConstraint("version >= 1", name="ck_policy_versions_version"),
        CheckConstraint(
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_policy_versions_action",
        ),
        CheckConstraint(
            "condition_mode IN ('all', 'any')", name="ck_policy_versions_condition_mode"
        ),
        Index("ix_policy_versions_lookup", "policy_id", "version"),
    )

    policy_version_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    policy_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(24))
    rationale_code: Mapped[str] = mapped_column(String(96))
    condition_mode: Mapped[str] = mapped_column(String(8))
    redaction_targets: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyCondition(Base):
    __tablename__ = "policy_conditions"
    __table_args__ = (
        UniqueConstraint("policy_version_id", "ordinal", name="uq_policy_conditions_ordinal"),
        CheckConstraint("ordinal BETWEEN 0 AND 19", name="ck_policy_conditions_ordinal"),
    )

    condition_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    policy_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("policy_versions.policy_version_id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(48))
    operator: Mapped[str] = mapped_column(String(32))
    value: Mapped[Any] = mapped_column(JSON)


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    __table_args__ = (
        CheckConstraint("phase IN ('input', 'output')", name="ck_policy_decisions_phase"),
        CheckConstraint(
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_policy_decisions_action",
        ),
        Index("ix_policy_decisions_analysis", "analysis_id"),
    )

    policy_decision_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_results.analysis_id", ondelete="CASCADE"), unique=True
    )
    risk_profile_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "risk_profile_versions.risk_profile_version_id",
            name="fk_policy_decisions_risk_profile_version",
        ),
    )
    phase: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(24))
    selected_policy_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("policies.policy_id"))
    selected_policy_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("policy_versions.policy_version_id")
    )
    scope_winners: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    evaluated_policy_versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    rationale_code: Mapped[str] = mapped_column(String(96))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
