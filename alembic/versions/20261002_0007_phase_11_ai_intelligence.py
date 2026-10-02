"""Phase 11 optional AI intelligence.

Revision ID: 20261002_0007
Revises: 20261002_0006
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261002_0007"
down_revision: str | None = "20261002_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_intelligence_configurations",
        sa.Column("config_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("environment_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("credential_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("credential_key_id", sa.String(80), nullable=True),
        sa.Column("allow_full_content", sa.Boolean(), nullable=False),
        sa.Column("connect_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("request_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("response_max_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('openai_compatible_remote', 'openai_compatible_local')",
            name="ck_ai_configs_kind",
        ),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_ai_configs_status"),
        sa.CheckConstraint(
            "environment_id IS NULL OR application_id IS NOT NULL",
            name="ck_ai_configs_environment_scope",
        ),
        sa.CheckConstraint(
            "(credential_ciphertext IS NULL AND credential_key_id IS NULL) OR "
            "(credential_ciphertext IS NOT NULL AND credential_key_id IS NOT NULL)",
            name="ck_ai_configs_credential_pair",
        ),
        sa.CheckConstraint(
            "connect_timeout_seconds BETWEEN 1 AND 10", name="ck_ai_connect_timeout"
        ),
        sa.CheckConstraint(
            "request_timeout_seconds BETWEEN 1 AND 120", name="ck_ai_request_timeout"
        ),
        sa.CheckConstraint(
            "response_max_bytes BETWEEN 1024 AND 131072", name="ck_ai_response_limit"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
            name="fk_ai_configs_organization",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            name="fk_ai_configs_application_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            name="fk_ai_configs_environment_tenant",
        ),
        sa.PrimaryKeyConstraint("config_id", name="pk_ai_intelligence_configurations"),
        sa.UniqueConstraint("config_id", "organization_id", name="uq_ai_configs_id_organization"),
        sa.UniqueConstraint("organization_id", "name_key", name="uq_ai_configs_org_name"),
    )
    for column in ("organization_id", "application_id", "environment_id", "status"):
        op.create_index(
            f"ix_ai_intelligence_configurations_{column}",
            "ai_intelligence_configurations",
            [column],
        )
    op.create_index(
        "ix_ai_configs_org_status", "ai_intelligence_configurations", ["organization_id", "status"]
    )

    op.create_table(
        "ai_intelligence_requests",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("config_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("task_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("context_mode", sa.String(24), nullable=False),
        sa.Column("incident_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_correlation_id", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "task_type IN ('incident_summary', 'attack_explanation', "
            "'mitigation_suggestion', 'policy_suggestion')",
            name="ck_ai_requests_task",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_ai_requests_status",
        ),
        sa.CheckConstraint(
            "context_mode IN ('metadata_only', 'redacted', 'full')",
            name="ck_ai_requests_context_mode",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_ai_requests_incident_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["config_id", "organization_id"],
            [
                "ai_intelligence_configurations.config_id",
                "ai_intelligence_configurations.organization_id",
            ],
            name="fk_ai_requests_config_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.user_id"], name="fk_ai_requests_user"
        ),
        sa.PrimaryKeyConstraint("request_id", name="pk_ai_intelligence_requests"),
        sa.UniqueConstraint("request_id", "organization_id", name="uq_ai_requests_id_organization"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_ai_requests_idempotency"
        ),
    )
    for column in ("organization_id", "incident_id", "config_id", "status"):
        op.create_index(
            f"ix_ai_intelligence_requests_{column}", "ai_intelligence_requests", [column]
        )
    op.create_index(
        "ix_ai_requests_org_incident_created",
        "ai_intelligence_requests",
        ["organization_id", "incident_id", "created_at"],
    )
    op.create_index(
        "ix_ai_requests_org_status_created",
        "ai_intelligence_requests",
        ["organization_id", "status", "created_at"],
    )
    op.create_index(
        "uq_ai_requests_inflight_task",
        "ai_intelligence_requests",
        ["organization_id", "incident_id", "task_type"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
        sqlite_where=sa.text("status IN ('pending', 'running')"),
    )

    op.create_table(
        "ai_intelligence_results",
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("config_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("prompt_template_version", sa.String(64), nullable=False),
        sa.Column("input_context_version", sa.String(32), nullable=False),
        sa.Column("output_schema_version", sa.String(32), nullable=False),
        sa.Column("structured_payload", sa.JSON(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="ck_ai_input_tokens"),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0", name="ck_ai_output_tokens"
        ),
        sa.CheckConstraint("total_tokens IS NULL OR total_tokens >= 0", name="ck_ai_total_tokens"),
        sa.ForeignKeyConstraint(
            ["config_id", "organization_id"],
            [
                "ai_intelligence_configurations.config_id",
                "ai_intelligence_configurations.organization_id",
            ],
            name="fk_ai_results_config_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["request_id", "organization_id"],
            ["ai_intelligence_requests.request_id", "ai_intelligence_requests.organization_id"],
            ondelete="CASCADE",
            name="fk_ai_results_request_tenant",
        ),
        sa.PrimaryKeyConstraint("result_id", name="pk_ai_intelligence_results"),
        sa.UniqueConstraint("request_id", name="uq_ai_results_request"),
    )
    for column in ("organization_id", "request_id", "config_id"):
        op.create_index(f"ix_ai_intelligence_results_{column}", "ai_intelligence_results", [column])
    op.create_index(
        "ix_ai_results_org_created",
        "ai_intelligence_results",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_ai_results_provider_created",
        "ai_intelligence_results",
        ["config_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_intelligence_results")
    op.drop_table("ai_intelligence_requests")
    op.drop_table("ai_intelligence_configurations")
