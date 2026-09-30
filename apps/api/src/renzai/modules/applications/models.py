"""Application persistence and privacy settings."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
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


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("organization_id", "name_key", name="uq_applications_org_name"),
        UniqueConstraint(
            "application_id", "organization_id", name="uq_applications_id_organization"
        ),
        CheckConstraint("status IN ('active', 'archived')", name="ck_applications_status"),
        CheckConstraint(
            "privacy_mode IN ('FULL', 'REDACTED', 'METADATA_ONLY')",
            name="ck_applications_privacy_mode",
        ),
        CheckConstraint(
            "security_retention_days BETWEEN 1 AND 365", name="ck_applications_retention"
        ),
        Index("ix_applications_organization_status", "organization_id", "status"),
    )

    application_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    name_key: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    privacy_mode: Mapped[str] = mapped_column(String(32), default="REDACTED")
    safe_content_persistence: Mapped[bool] = mapped_column(Boolean, default=False)
    security_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
