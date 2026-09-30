"""Organization persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
