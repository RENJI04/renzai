"""Phase 5 identity, sessions, organizations, memberships, and audit.

Revision ID: 20260924_0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("normalized_email", sa.String(320), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privilege_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"], unique=True)
    op.create_index("ix_users_status", "users", ["status"])
    op.create_table(
        "password_credentials",
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False),
        sa.Column("parameters_version", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("credential_id"),
    )
    op.create_index(
        "ix_password_credentials_user_id", "password_credentials", ["user_id"], unique=True
    )
    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("organization_id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lookup", sa.String(32), nullable=False),
        sa.Column("verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("verifier_key_id", sa.String(32), nullable=False),
        sa.Column("csrf_verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("privilege_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_sessions_lookup", "sessions", ["lookup"], unique=True)
    for column in ("user_id", "idle_expires_at", "absolute_expires_at", "revoked_at"):
        op.create_index(f"ix_sessions_{column}", "sessions", [column])
    op.create_table(
        "password_reset_tokens",
        sa.Column("reset_token_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lookup", sa.String(32), nullable=False),
        sa.Column("verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("verifier_key_id", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("reset_token_id"),
    )
    op.create_index(
        "ix_password_reset_tokens_lookup", "password_reset_tokens", ["lookup"], unique=True
    )
    for column in ("user_id", "expires_at"):
        op.create_index(f"ix_password_reset_tokens_{column}", "password_reset_tokens", [column])
    op.create_table(
        "email_verification_tokens",
        sa.Column("verification_token_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lookup", sa.String(32), nullable=False),
        sa.Column("verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("verifier_key_id", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("verification_token_id"),
    )
    op.create_index(
        "ix_email_verification_tokens_lookup",
        "email_verification_tokens",
        ["lookup"],
        unique=True,
    )
    for column in ("user_id", "expires_at"):
        op.create_index(
            f"ix_email_verification_tokens_{column}", "email_verification_tokens", [column]
        )
    op.create_table(
        "memberships",
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("membership_id"),
        sa.UniqueConstraint("organization_id", "user_id"),
    )
    for column in ("organization_id", "user_id", "role", "status"):
        op.create_index(f"ix_memberships_{column}", "memberships", [column])
    op.create_table(
        "invitations",
        sa.Column("invitation_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("lookup", sa.String(32), nullable=False),
        sa.Column("verifier", sa.LargeBinary(32), nullable=False),
        sa.Column("verifier_key_id", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("invitation_id"),
    )
    op.create_index("ix_invitations_lookup", "invitations", ["lookup"], unique=True)
    for column in ("organization_id", "target_email", "expires_at"):
        op.create_index(f"ix_invitations_{column}", "invitations", [column])
    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("audit_event_id"),
    )
    for column in ("organization_id", "action", "created_at"):
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])
    op.create_table(
        "account_security_events",
        sa.Column("account_security_event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("account_security_event_id"),
    )
    for column in ("user_id", "action", "created_at"):
        op.create_index(f"ix_account_security_events_{column}", "account_security_events", [column])


def downgrade() -> None:
    op.drop_table("account_security_events")
    op.drop_table("audit_events")
    op.drop_table("invitations")
    op.drop_table("memberships")
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("sessions")
    op.drop_table("organizations")
    op.drop_table("password_credentials")
    op.drop_table("users")
