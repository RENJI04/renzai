"""Persistent risk profiles and immutable analysis contributions."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_risk_profiles_status"),
        UniqueConstraint("organization_id", "name", name="uq_risk_profiles_organization_name"),
        Index("ix_risk_profiles_active", "organization_id", "status", "active_version"),
    )

    risk_profile_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(String(80))
    active_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="active")
    system_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class RiskProfileVersion(Base):
    __tablename__ = "risk_profile_versions"
    __table_args__ = (
        UniqueConstraint("risk_profile_id", "version", name="uq_risk_profile_versions_number"),
        CheckConstraint("version >= 1", name="ck_risk_profile_versions_version"),
        Index("ix_risk_profile_versions_lookup", "risk_profile_id", "version"),
    )

    risk_profile_version_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    risk_profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("risk_profiles.risk_profile_id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict[str, int]] = mapped_column(JSON)
    thresholds: Mapped[dict[str, int]] = mapped_column(JSON)
    formula_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    formula_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RiskContribution(Base):
    __tablename__ = "risk_contributions"
    __table_args__ = (
        CheckConstraint("base_weight BETWEEN 0 AND 100", name="ck_risk_contributions_base"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_risk_contributions_confidence"),
        CheckConstraint("raw_contribution BETWEEN 0 AND 100", name="ck_risk_contributions_raw"),
        CheckConstraint(
            "status IN ('retained', 'suppressed')", name="ck_risk_contributions_status"
        ),
        Index("ix_risk_contributions_analysis", "analysis_id", "status"),
    )

    contribution_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_results.analysis_id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("findings.finding_id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(64))
    detector_id: Mapped[str] = mapped_column(String(96))
    detector_version: Mapped[str] = mapped_column(String(32))
    base_weight: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[int] = mapped_column(Integer)
    raw_contribution: Mapped[int] = mapped_column(Integer)
    overlap_group: Mapped[str] = mapped_column(String(96))
    status: Mapped[str] = mapped_column(String(24))
    suppressed_by_finding_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("findings.finding_id")
    )
    corroboration_bonus: Mapped[int] = mapped_column(Integer, default=0)
    critical_floor_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
