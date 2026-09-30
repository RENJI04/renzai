"""Tenant-scoped provider configuration persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class ProviderConfiguration(Base):
    __tablename__ = "provider_configurations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_provider_configs_environment_tenant",
        ),
        UniqueConstraint(
            "provider_id",
            "environment_id",
            "application_id",
            "organization_id",
            name="uq_provider_configs_id_tenant",
        ),
        UniqueConstraint("environment_id", "name_key", name="uq_provider_configs_environment_name"),
        CheckConstraint(
            "kind IN ('openai_compatible_remote', 'openai_compatible_local')",
            name="ck_provider_configs_kind",
        ),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_provider_configs_status"),
        CheckConstraint(
            "last_validation_status IN ('never', 'success', 'failure')",
            name="ck_provider_configs_validation_status",
        ),
        CheckConstraint(
            "(credential_ciphertext IS NULL AND credential_key_id IS NULL) OR "
            "(credential_ciphertext IS NOT NULL AND credential_key_id IS NOT NULL)",
            name="ck_provider_configs_credential_pair",
        ),
        CheckConstraint(
            "connect_timeout_seconds BETWEEN 1 AND 10",
            name="ck_provider_configs_connect_timeout",
        ),
        CheckConstraint(
            "chat_timeout_seconds BETWEEN 1 AND 120",
            name="ck_provider_configs_chat_timeout",
        ),
        CheckConstraint(
            "health_timeout_seconds BETWEEN 1 AND 15",
            name="ck_provider_configs_health_timeout",
        ),
        CheckConstraint(
            "response_max_bytes BETWEEN 1024 AND 524288",
            name="ck_provider_configs_response_limit",
        ),
        CheckConstraint("max_tokens BETWEEN 1 AND 4096", name="ck_provider_configs_max_tokens"),
        Index(
            "ix_provider_configs_environment_status",
            "organization_id",
            "application_id",
            "environment_id",
            "status",
        ),
    )

    provider_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    kind: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(String(120))
    name_key: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str] = mapped_column(String(512))
    model: Mapped[str] = mapped_column(String(160), index=True)
    credential_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    credential_key_id: Mapped[str | None] = mapped_column(String(80))
    supports_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    connect_timeout_seconds: Mapped[int] = mapped_column(Integer, default=3)
    chat_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    health_timeout_seconds: Mapped[int] = mapped_column(Integer, default=5)
    response_max_bytes: Mapped[int] = mapped_column(Integer, default=128 * 1024)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    validation_policy_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    last_validation_status: Mapped[str] = mapped_column(String(24), default="never")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
