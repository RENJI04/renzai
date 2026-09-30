"""Phase 8 encrypted providers and limited Gateway persistence.

Revision ID: 20260928_0004
Revises: 20260927_0003
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_0004"
down_revision: str | None = "20260927_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_configurations",
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("credential_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("credential_key_id", sa.String(80), nullable=True),
        sa.Column("supports_seed", sa.Boolean(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("connect_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("chat_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("health_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("response_max_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("validation_policy_version", sa.String(32), nullable=False),
        sa.Column("last_validation_status", sa.String(24), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('openai_compatible_remote', 'openai_compatible_local')",
            name="ck_provider_configs_kind",
        ),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_provider_configs_status"),
        sa.CheckConstraint(
            "last_validation_status IN ('never', 'success', 'failure')",
            name="ck_provider_configs_validation_status",
        ),
        sa.CheckConstraint(
            "(credential_ciphertext IS NULL AND credential_key_id IS NULL) OR "
            "(credential_ciphertext IS NOT NULL AND credential_key_id IS NOT NULL)",
            name="ck_provider_configs_credential_pair",
        ),
        sa.CheckConstraint(
            "connect_timeout_seconds BETWEEN 1 AND 10",
            name="ck_provider_configs_connect_timeout",
        ),
        sa.CheckConstraint(
            "chat_timeout_seconds BETWEEN 1 AND 120",
            name="ck_provider_configs_chat_timeout",
        ),
        sa.CheckConstraint(
            "health_timeout_seconds BETWEEN 1 AND 15",
            name="ck_provider_configs_health_timeout",
        ),
        sa.CheckConstraint(
            "response_max_bytes BETWEEN 1024 AND 524288",
            name="ck_provider_configs_response_limit",
        ),
        sa.CheckConstraint("max_tokens BETWEEN 1 AND 4096", name="ck_provider_configs_max_tokens"),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_provider_configs_environment_tenant",
        ),
        sa.PrimaryKeyConstraint("provider_id", name="pk_provider_configurations"),
        sa.UniqueConstraint(
            "provider_id",
            "environment_id",
            "application_id",
            "organization_id",
            name="uq_provider_configs_id_tenant",
        ),
        sa.UniqueConstraint(
            "environment_id", "name_key", name="uq_provider_configs_environment_name"
        ),
    )
    for column in ("organization_id", "application_id", "environment_id", "model"):
        op.create_index(f"ix_provider_configurations_{column}", "provider_configurations", [column])
    op.create_index("ix_provider_configurations_status", "provider_configurations", ["status"])
    op.create_index(
        "ix_provider_configs_environment_status",
        "provider_configurations",
        ["organization_id", "application_id", "environment_id", "status"],
    )

    op.create_table(
        "gateway_provider_calls",
        sa.Column("gateway_call_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("input_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("output_analysis_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("configured_model", sa.String(160), nullable=False),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=False),
        sa.Column("status_class", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('completed', 'provider_timeout', 'provider_error', 'configuration_error', "
            "'output_block', 'output_review', 'output_inspection_failure')",
            name="ck_gateway_calls_outcome",
        ),
        sa.CheckConstraint(
            "status_class IS NULL OR status_class BETWEEN 1 AND 5",
            name="ck_gateway_calls_status_class",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id", "environment_id", "application_id", "organization_id"],
            [
                "provider_configurations.provider_id",
                "provider_configurations.environment_id",
                "provider_configurations.application_id",
                "provider_configurations.organization_id",
            ],
            name="fk_gateway_calls_provider_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["input_analysis_id"],
            ["analysis_results.analysis_id"],
            name="fk_gateway_calls_input_analysis",
        ),
        sa.ForeignKeyConstraint(
            ["output_analysis_id"],
            ["analysis_results.analysis_id"],
            name="fk_gateway_calls_output_analysis",
        ),
        sa.PrimaryKeyConstraint("gateway_call_id", name="pk_gateway_provider_calls"),
    )
    for column in (
        "organization_id",
        "application_id",
        "environment_id",
        "provider_id",
        "input_analysis_id",
        "output_analysis_id",
        "correlation_id",
        "outcome",
    ):
        op.create_index(f"ix_gateway_provider_calls_{column}", "gateway_provider_calls", [column])
    op.create_index(
        "ix_gateway_calls_scope_time",
        "gateway_provider_calls",
        ["organization_id", "application_id", "environment_id", "created_at"],
    )

    with op.batch_alter_table("security_events") as batch:
        batch.drop_constraint("ck_security_events_source", type_="check")
        batch.create_check_constraint(
            "ck_security_events_source",
            "source IN ('analyze', 'playground', 'gateway')",
        )


def downgrade() -> None:
    with op.batch_alter_table("security_events") as batch:
        batch.drop_constraint("ck_security_events_source", type_="check")
        batch.create_check_constraint(
            "ck_security_events_source", "source IN ('analyze', 'playground')"
        )
    op.drop_table("gateway_provider_calls")
    op.drop_table("provider_configurations")
