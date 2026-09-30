"""Phase 6 applications, environment keys, and deterministic analysis persistence.

Revision ID: 20260926_0002
Revises: 20260924_0001
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0002"
down_revision: str | None = "20260924_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("privacy_mode", sa.String(32), nullable=False),
        sa.Column("safe_content_persistence", sa.Boolean(), nullable=False),
        sa.Column("security_retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_applications_status"),
        sa.CheckConstraint(
            "privacy_mode IN ('FULL', 'REDACTED', 'METADATA_ONLY')",
            name="ck_applications_privacy_mode",
        ),
        sa.CheckConstraint(
            "security_retention_days BETWEEN 1 AND 365", name="ck_applications_retention"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("application_id"),
        sa.UniqueConstraint(
            "application_id", "organization_id", name="uq_applications_id_organization"
        ),
        sa.UniqueConstraint("organization_id", "name_key", name="uq_applications_org_name"),
    )
    op.create_index("ix_applications_organization_id", "applications", ["organization_id"])
    op.create_index(
        "ix_applications_organization_status",
        "applications",
        ["organization_id", "status"],
    )
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "environments",
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('development', 'staging', 'production')", name="ck_environments_type"
        ),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_environments_status"),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            ondelete="CASCADE",
            name="fk_environments_application_tenant",
        ),
        sa.PrimaryKeyConstraint("environment_id"),
        sa.UniqueConstraint("application_id", "type", name="uq_environments_application_type"),
        sa.UniqueConstraint(
            "environment_id",
            "application_id",
            "organization_id",
            name="uq_environments_id_application_organization",
        ),
    )
    op.create_index("ix_environments_application_id", "environments", ["application_id"])
    op.create_index(
        "ix_environments_application_status", "environments", ["application_id", "status"]
    )
    op.create_index("ix_environments_organization_id", "environments", ["organization_id"])
    op.create_index("ix_environments_type", "environments", ["type"])

    op.create_table(
        "application_api_keys",
        sa.Column("key_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("lookup", sa.String(22), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("verifier_key_id", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_application_api_keys_environment_tenant",
        ),
        sa.PrimaryKeyConstraint("key_id"),
    )
    for column in ("organization_id", "application_id", "environment_id"):
        op.create_index(f"ix_application_api_keys_{column}", "application_api_keys", [column])
    op.create_index(
        "ix_application_api_keys_lookup", "application_api_keys", ["lookup"], unique=True
    )
    op.create_index(
        "ix_application_api_keys_environment_state",
        "application_api_keys",
        ["environment_id", "revoked_at"],
    )
    op.create_index("ix_application_api_keys_expiry", "application_api_keys", ["expires_at"])

    op.create_table(
        "security_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("privacy_mode", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_bytes", sa.Integer(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.CheckConstraint("direction IN ('input', 'output')", name="ck_security_events_direction"),
        sa.CheckConstraint("source IN ('analyze', 'playground')", name="ck_security_events_source"),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_security_events_environment_tenant",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    for column in (
        "organization_id",
        "application_id",
        "environment_id",
        "direction",
        "source",
        "correlation_id",
    ):
        op.create_index(f"ix_security_events_{column}", "security_events", [column])
    op.create_index(
        "ix_security_events_scope_time",
        "security_events",
        ["organization_id", "application_id", "environment_id", "occurred_at"],
    )

    op.create_table(
        "analysis_results",
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("normalization_version", sa.String(32), nullable=False),
        sa.Column("ruleset_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("normalization_ms", sa.Integer(), nullable=False),
        sa.Column("detector_ms", sa.Integer(), nullable=False),
        sa.Column("total_ms", sa.Integer(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["security_events.event_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    op.create_index("ix_analysis_results_event_id", "analysis_results", ["event_id"], unique=True)

    op.create_table(
        "findings",
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("detector_id", sa.String(96), nullable=False),
        sa.Column("detector_version", sa.String(32), nullable=False),
        sa.Column("ruleset_version", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("safe_explanation", sa.String(320), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("overlap_group", sa.String(64), nullable=True),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_findings_confidence"),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis_results.analysis_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("finding_id"),
    )
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])
    op.create_index("ix_findings_analysis_category", "findings", ["analysis_id", "category"])
    op.create_index("ix_findings_category", "findings", ["category"])
    op.create_index("ix_findings_detector", "findings", ["detector_id"])


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("analysis_results")
    op.drop_table("security_events")
    op.drop_table("application_api_keys")
    op.drop_table("environments")
    op.drop_table("applications")
