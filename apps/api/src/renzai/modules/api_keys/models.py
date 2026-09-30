"""Verifier-only environment-scoped application API keys."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class ApplicationApiKey(Base):
    __tablename__ = "application_api_keys"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_application_api_keys_environment_tenant",
        ),
        Index("ix_application_api_keys_environment_state", "environment_id", "revoked_at"),
        Index("ix_application_api_keys_expiry", "expires_at"),
    )

    key_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.user_id"))
    label: Mapped[str] = mapped_column(String(80))
    lookup: Mapped[str] = mapped_column(String(22), unique=True, index=True)
    prefix: Mapped[str] = mapped_column(String(20))
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    verifier_key_id: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
