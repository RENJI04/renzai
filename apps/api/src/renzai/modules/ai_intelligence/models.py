"""Tenant-scoped optional AI intelligence persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class AIIntelligenceConfiguration(Base):
    __tablename__ = "ai_intelligence_configurations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            name="fk_ai_configs_application_tenant",
        ),
        ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            name="fk_ai_configs_environment_tenant",
        ),
        UniqueConstraint("config_id", "organization_id", name="uq_ai_configs_id_organization"),
        UniqueConstraint("organization_id", "name_key", name="uq_ai_configs_org_name"),
        CheckConstraint(
            "kind IN ('openai_compatible_remote', 'openai_compatible_local')",
            name="ck_ai_configs_kind",
        ),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_ai_configs_status"),
        CheckConstraint(
            "environment_id IS NULL OR application_id IS NOT NULL",
            name="ck_ai_configs_environment_scope",
        ),
        CheckConstraint(
            "(credential_ciphertext IS NULL AND credential_key_id IS NULL) OR "
            "(credential_ciphertext IS NOT NULL AND credential_key_id IS NOT NULL)",
            name="ck_ai_configs_credential_pair",
        ),
        CheckConstraint("connect_timeout_seconds BETWEEN 1 AND 10", name="ck_ai_connect_timeout"),
        CheckConstraint("request_timeout_seconds BETWEEN 1 AND 120", name="ck_ai_request_timeout"),
        CheckConstraint("response_max_bytes BETWEEN 1024 AND 131072", name="ck_ai_response_limit"),
        Index("ix_ai_configs_org_status", "organization_id", "status"),
    )

    config_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.organization_id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(String(120))
    name_key: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(48))
    base_url: Mapped[str] = mapped_column(String(512))
    model: Mapped[str] = mapped_column(String(160))
    credential_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    credential_key_id: Mapped[str | None] = mapped_column(String(80))
    allow_full_content: Mapped[bool] = mapped_column(Boolean, default=False)
    connect_timeout_seconds: Mapped[int] = mapped_column(Integer, default=3)
    request_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    response_max_bytes: Mapped[int] = mapped_column(Integer, default=64 * 1024)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AIIntelligenceRequest(Base):
    __tablename__ = "ai_intelligence_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_ai_requests_incident_tenant",
        ),
        ForeignKeyConstraint(
            ["config_id", "organization_id"],
            [
                "ai_intelligence_configurations.config_id",
                "ai_intelligence_configurations.organization_id",
            ],
            name="fk_ai_requests_config_tenant",
        ),
        UniqueConstraint("request_id", "organization_id", name="uq_ai_requests_id_organization"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_ai_requests_idempotency"),
        CheckConstraint(
            "task_type IN ('incident_summary', 'attack_explanation', "
            "'mitigation_suggestion', 'policy_suggestion')",
            name="ck_ai_requests_task",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_ai_requests_status",
        ),
        CheckConstraint(
            "context_mode IN ('metadata_only', 'redacted', 'full')",
            name="ck_ai_requests_context_mode",
        ),
        Index(
            "ix_ai_requests_org_incident_created", "organization_id", "incident_id", "created_at"
        ),
        Index("ix_ai_requests_org_status_created", "organization_id", "status", "created_at"),
        Index(
            "uq_ai_requests_inflight_task",
            "organization_id",
            "incident_id",
            "task_type",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
            sqlite_where=text("status IN ('pending', 'running')"),
        ),
    )

    request_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    incident_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    config_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.user_id"))
    task_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    context_mode: Mapped[str] = mapped_column(String(24))
    incident_version: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_correlation_id: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIIntelligenceResult(Base):
    __tablename__ = "ai_intelligence_results"
    __table_args__ = (
        ForeignKeyConstraint(
            ["config_id", "organization_id"],
            [
                "ai_intelligence_configurations.config_id",
                "ai_intelligence_configurations.organization_id",
            ],
            name="fk_ai_results_config_tenant",
        ),
        ForeignKeyConstraint(
            ["request_id", "organization_id"],
            ["ai_intelligence_requests.request_id", "ai_intelligence_requests.organization_id"],
            ondelete="CASCADE",
            name="fk_ai_results_request_tenant",
        ),
        UniqueConstraint("request_id", name="uq_ai_results_request"),
        CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="ck_ai_input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="ck_ai_output_tokens"),
        CheckConstraint("total_tokens IS NULL OR total_tokens >= 0", name="ck_ai_total_tokens"),
        Index("ix_ai_results_org_created", "organization_id", "created_at"),
        Index("ix_ai_results_provider_created", "config_id", "created_at"),
    )

    result_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    request_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    config_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    model: Mapped[str] = mapped_column(String(160))
    prompt_template_version: Mapped[str] = mapped_column(String(64))
    input_context_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    output_schema_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    structured_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
