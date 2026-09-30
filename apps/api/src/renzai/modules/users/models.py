"""User and password credential persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    email: Mapped[str] = mapped_column(String(320))
    normalized_email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privilege_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PasswordCredential(Base):
    __tablename__ = "password_credentials"

    credential_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(512))
    algorithm: Mapped[str] = mapped_column(String(32), default="argon2id")
    parameters_version: Mapped[int] = mapped_column(Integer, default=1)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
