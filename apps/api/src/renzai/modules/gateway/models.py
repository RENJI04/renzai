"""Safe provider-call metadata for Gateway observability."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from renzai.core.ids import new_uuid7
from renzai.core.time import utc_now
from renzai.db.base import Base


class GatewayProviderCall(Base):
    __tablename__ = "gateway_provider_calls"
    __table_args__ = (
        ForeignKeyConstraint(
            ["provider_id", "environment_id", "application_id", "organization_id"],
            [
                "provider_configurations.provider_id",
                "provider_configurations.environment_id",
                "provider_configurations.application_id",
                "provider_configurations.organization_id",
            ],
            name="fk_gateway_calls_provider_tenant",
        ),
        CheckConstraint(
            "outcome IN ('completed', 'provider_timeout', 'provider_error', 'configuration_error', "
            "'output_block', 'output_review', 'output_inspection_failure')",
            name="ck_gateway_calls_outcome",
        ),
        CheckConstraint(
            "status_class IS NULL OR status_class BETWEEN 1 AND 5",
            name="ck_gateway_calls_status_class",
        ),
        Index(
            "ix_gateway_calls_scope_time",
            "organization_id",
            "application_id",
            "environment_id",
            "created_at",
        ),
        Index("ix_gateway_calls_org_time", "organization_id", "created_at"),
        Index(
            "ix_gateway_calls_org_provider_time",
            "organization_id",
            "provider_id",
            "created_at",
        ),
    )

    gateway_call_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid7)
    organization_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    application_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    environment_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    provider_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    input_analysis_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("analysis_results.analysis_id"), index=True
    )
    output_analysis_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("analysis_results.analysis_id"), index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    configured_model: Mapped[str] = mapped_column(String(160))
    provider_latency_ms: Mapped[int] = mapped_column(Integer)
    status_class: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
