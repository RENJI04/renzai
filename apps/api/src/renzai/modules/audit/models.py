"""Tenant audit and separate global account-security event persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.user_id"))
    action: Mapped[str] = mapped_column(String(96), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(128))
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class AccountSecurityEvent(Base):
    __tablename__ = "account_security_events"

    account_security_event_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=new_uuid7
    )
    user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.user_id"), index=True)
    action: Mapped[str] = mapped_column(String(96), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(128))
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
