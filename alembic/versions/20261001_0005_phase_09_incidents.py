"""Phase 9 tenant-scoped incident management.

Revision ID: 20261001_0005
Revises: 20260928_0004
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_0005"
down_revision: str | None = "20260928_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("security_events") as batch:
        batch.create_unique_constraint(
            "uq_security_events_id_organization", ["event_id", "organization_id"]
        )
    with op.batch_alter_table("analysis_results") as batch:
        batch.create_unique_constraint("uq_analysis_results_id_event", ["analysis_id", "event_id"])

    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("environment_id", sa.Uuid(), nullable=True),
        sa.Column("primary_event_id", sa.Uuid(), nullable=True),
        sa.Column("primary_analysis_id", sa.Uuid(), nullable=True),
        sa.Column("trigger_rule_id", sa.String(160), nullable=True),
        sa.Column("manual_idempotency_key", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("detector_id", sa.String(96), nullable=True),
        sa.Column("action", sa.String(24), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("direction", sa.String(16), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("safe_summary", sa.String(500), nullable=False),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_category", sa.String(32), nullable=True),
        sa.Column("resolution_reason", sa.String(500), nullable=True),
        sa.Column("privacy_mode", sa.String(32), nullable=True),
        sa.Column("security_retention_days", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'ignored', 'false_positive')",
            name="ck_incidents_status",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_incidents_severity",
        ),
        sa.CheckConstraint(
            "risk_score IS NULL OR risk_score BETWEEN 0 AND 100", name="ck_incidents_risk"
        ),
        sa.CheckConstraint(
            "action IS NULL OR action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_incidents_action",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'gateway', 'analyze', 'playground')",
            name="ck_incidents_source",
        ),
        sa.CheckConstraint(
            "(primary_event_id IS NULL AND primary_analysis_id IS NULL "
            "AND trigger_rule_id IS NULL) "
            "OR (primary_event_id IS NOT NULL AND primary_analysis_id IS NOT NULL "
            "AND trigger_rule_id IS NOT NULL)",
            name="ck_incidents_trigger_shape",
        ),
        sa.CheckConstraint(
            "environment_id IS NULL OR application_id IS NOT NULL",
            name="ck_incidents_environment_scope",
        ),
        sa.CheckConstraint("version >= 1", name="ck_incidents_version"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.organization_id"], name="fk_incidents_organization"
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            name="fk_incidents_application_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            name="fk_incidents_environment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assignee_user_id"],
            ["memberships.organization_id", "memberships.user_id"],
            name="fk_incidents_assignee_membership",
        ),
        sa.PrimaryKeyConstraint("incident_id", name="pk_incidents"),
        sa.UniqueConstraint("incident_id", "organization_id", name="uq_incidents_id_organization"),
        sa.UniqueConstraint(
            "organization_id",
            "primary_event_id",
            "trigger_rule_id",
            name="uq_incidents_automatic_identity",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "manual_idempotency_key",
            name="uq_incidents_manual_idempotency",
        ),
    )
    for column in (
        "organization_id",
        "application_id",
        "environment_id",
        "primary_event_id",
        "primary_analysis_id",
        "status",
        "severity",
        "category",
        "action",
        "source",
        "assignee_user_id",
    ):
        op.create_index(f"ix_incidents_{column}", "incidents", [column])
    op.create_index(
        "ix_incidents_org_status_created",
        "incidents",
        ["organization_id", "status", "created_at"],
    )
    op.create_index(
        "ix_incidents_org_severity_created",
        "incidents",
        ["organization_id", "severity", "created_at"],
    )
    op.create_index(
        "ix_incidents_org_assignee_created",
        "incidents",
        ["organization_id", "assignee_user_id", "created_at"],
    )
    op.create_index(
        "ix_incidents_scope_created",
        "incidents",
        ["organization_id", "application_id", "environment_id", "created_at"],
    )

    op.create_table(
        "incident_security_events",
        sa.Column("relation_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_events_incident_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["security_events.event_id", "security_events.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_events_event_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id", "event_id"],
            ["analysis_results.analysis_id", "analysis_results.event_id"],
            ondelete="CASCADE",
            name="fk_incident_events_analysis_event",
        ),
        sa.PrimaryKeyConstraint("relation_id", name="pk_incident_security_events"),
        sa.UniqueConstraint("incident_id", "analysis_id", name="uq_incident_events_analysis"),
    )
    for column in ("organization_id", "incident_id", "event_id", "analysis_id"):
        op.create_index(
            f"ix_incident_security_events_{column}", "incident_security_events", [column]
        )

    op.create_table(
        "incident_comments",
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 4000", name="ck_incident_comments_body"),
        sa.ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_comments_incident_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.user_id"], name="fk_incident_comments_author"
        ),
        sa.PrimaryKeyConstraint("comment_id", name="pk_incident_comments"),
    )
    for column in ("organization_id", "incident_id", "author_user_id"):
        op.create_index(f"ix_incident_comments_{column}", "incident_comments", [column])
    op.create_index(
        "ix_incident_comments_incident_created",
        "incident_comments",
        ["incident_id", "created_at"],
    )

    op.create_table(
        "incident_timeline_events",
        sa.Column("timeline_event_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("safe_summary", sa.String(500), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=True),
        sa.Column("referenced_event_id", sa.Uuid(), nullable=True),
        sa.Column("referenced_policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('incident_created', 'status_changed', 'assigned', 'unassigned', "
            "'comment_added', 'false_positive_marked', 'related_event_added', "
            "'policy_action_recorded')",
            name="ck_incident_timeline_type",
        ),
        sa.CheckConstraint("actor_type IN ('user', 'service')", name="ck_incident_timeline_actor"),
        sa.ForeignKeyConstraint(
            ["incident_id", "organization_id"],
            ["incidents.incident_id", "incidents.organization_id"],
            ondelete="CASCADE",
            name="fk_incident_timeline_incident_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.user_id"], name="fk_incident_timeline_actor_user"
        ),
        sa.PrimaryKeyConstraint("timeline_event_id", name="pk_incident_timeline_events"),
    )
    for column in (
        "organization_id",
        "incident_id",
        "event_type",
        "correlation_id",
    ):
        op.create_index(
            f"ix_incident_timeline_events_{column}", "incident_timeline_events", [column]
        )
    op.create_index(
        "ix_incident_timeline_incident_created",
        "incident_timeline_events",
        ["incident_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("incident_timeline_events")
    op.drop_table("incident_comments")
    op.drop_table("incident_security_events")
    op.drop_table("incidents")
    with op.batch_alter_table("analysis_results") as batch:
        batch.drop_constraint("uq_analysis_results_id_event", type_="unique")
    with op.batch_alter_table("security_events") as batch:
        batch.drop_constraint("uq_security_events_id_organization", type_="unique")
