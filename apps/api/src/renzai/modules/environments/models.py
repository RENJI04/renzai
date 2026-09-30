"""Application environment persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            ondelete="CASCADE",
            name="fk_environments_application_tenant",
        ),
        UniqueConstraint("application_id", "type", name="uq_environments_application_type"),
        UniqueConstraint(
            "environment_id",
            "application_id",
            "organization_id",
            name="uq_environments_id_application_organization",
        ),
        CheckConstraint(
            "type IN ('development', 'staging', 'production')", name="ck_environments_type"
        ),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_environments_status"),
        Index("ix_environments_application_status", "application_id", "status"),
    )

    environment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
