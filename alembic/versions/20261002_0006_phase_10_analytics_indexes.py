"""Phase 10 operational analytics indexes.

Revision ID: 20261002_0006
Revises: 20261001_0005
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261002_0006"
down_revision: str | None = "20261001_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_security_events_org_time", "security_events", ["organization_id", "occurred_at"]
    )
    op.create_index(
        "ix_gateway_calls_org_time",
        "gateway_provider_calls",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_gateway_calls_org_provider_time",
        "gateway_provider_calls",
        ["organization_id", "provider_id", "created_at"],
    )
    op.create_index("ix_incidents_org_created", "incidents", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_incidents_org_created", table_name="incidents")
    op.drop_index("ix_gateway_calls_org_provider_time", table_name="gateway_provider_calls")
    op.drop_index("ix_gateway_calls_org_time", table_name="gateway_provider_calls")
    op.drop_index("ix_security_events_org_time", table_name="security_events")
