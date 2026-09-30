"""Opaque session and single-use identity token persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    lookup: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    verifier_key_id: Mapped[str] = mapped_column(String(32))
    csrf_verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    privilege_version: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    reset_token_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    lookup: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    verifier_key_id: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    verification_token_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    lookup: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    verifier: Mapped[bytes] = mapped_column(LargeBinary(32))
    verifier_key_id: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
