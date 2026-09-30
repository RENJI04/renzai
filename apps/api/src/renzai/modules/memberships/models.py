"""Organization membership and invitation persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    membership_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Invitation(Base):
    __tablename__ = "invitations"

    invitation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.user_id"))
    target_email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(32))
    lookup: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    verifier_key_id: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
