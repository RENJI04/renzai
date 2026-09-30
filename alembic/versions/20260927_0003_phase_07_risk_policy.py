"""Phase 7 deterministic risk scoring and tenant-scoped policy enforcement.

Revision ID: 20260927_0003
Revises: 20260926_0002
Create Date: 2026-09-27
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260927_0003"
down_revision: str | None = "20260926_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROFILE_ID = UUID("71000000-0000-7000-8000-000000000001")
PROFILE_VERSION_ID = UUID("71000000-0000-7000-8000-000000000002")
WEIGHTS = {
    "prompt_injection": 55,
    "instruction_override": 45,
    "system_prompt_extraction": 55,
    "jailbreak": 50,
    "role_manipulation": 40,
    "encoded_obfuscated": 35,
    "secret_exposure": 80,
    "pii_exposure": 55,
    "suspicious_url": 20,
    "tool_manipulation_indicator": 45,
    "data_exfiltration_indicator": 60,
}
BASELINES = (
    ("v1.input.critical", "V1 Input Critical", "input", 100, "block", "critical", ()),
    (
        "v1.input.high",
        "V1 Input High",
        "input",
        200,
        "require_review",
        "high",
        (),
    ),
    ("v1.input.medium", "V1 Input Medium", "input", 300, "flag", "medium", ()),
    ("v1.input.low", "V1 Input Low", "input", 400, "allow", "low", ()),
    (
        "v1.output.secret_exposure",
        "V1 Output Secret Redaction",
        "output",
        50,
        "redact",
        "secret_exposure",
        ("secret_exposure",),
    ),
    ("v1.output.critical", "V1 Output Critical", "output", 100, "block", "critical", ()),
    (
        "v1.output.high",
        "V1 Output High",
        "output",
        200,
        "require_review",
        "high",
        (),
    ),
    ("v1.output.medium", "V1 Output Medium", "output", 300, "flag", "medium", ()),
    ("v1.output.low", "V1 Output Low", "output", 400, "allow", "low", ()),
)


def upgrade() -> None:
    _create_risk_tables()
    _create_policy_tables()
    _extend_analysis_tables()
    _create_evidence_tables()
    _seed_profile_and_baselines()


def _create_risk_tables() -> None:
    op.create_table(
        "risk_profiles",
        sa.Column("risk_profile_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("active_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("system_owned", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_risk_profiles_ck_risk_profiles_status",
        ),
        sa.PrimaryKeyConstraint("risk_profile_id", name="pk_risk_profiles"),
        sa.UniqueConstraint("organization_id", "name", name="uq_risk_profiles_organization_name"),
    )
    op.create_index("ix_risk_profiles_organization_id", "risk_profiles", ["organization_id"])
    op.create_index(
        "ix_risk_profiles_active",
        "risk_profiles",
        ["organization_id", "status", "active_version"],
    )
    op.create_table(
        "risk_profile_versions",
        sa.Column("risk_profile_version_id", sa.Uuid(), nullable=False),
        sa.Column("risk_profile_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("formula_metadata", sa.JSON(), nullable=False),
        sa.Column("formula_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_risk_profile_versions_ck_risk_profile_versions_version",
        ),
        sa.ForeignKeyConstraint(
            ["risk_profile_id"],
            ["risk_profiles.risk_profile_id"],
            ondelete="CASCADE",
            name="fk_risk_profile_versions_risk_profile_id_risk_profiles",
        ),
        sa.PrimaryKeyConstraint("risk_profile_version_id", name="pk_risk_profile_versions"),
        sa.UniqueConstraint("risk_profile_id", "version", name="uq_risk_profile_versions_number"),
    )
    op.create_index(
        "ix_risk_profile_versions_risk_profile_id",
        "risk_profile_versions",
        ["risk_profile_id"],
    )
    op.create_index(
        "ix_risk_profile_versions_lookup",
        "risk_profile_versions",
        ["risk_profile_id", "version"],
    )


def _create_policy_tables() -> None:
    op.create_table(
        "policies",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("environment_id", sa.Uuid(), nullable=True),
        sa.Column("scope_kind", sa.String(24), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("active_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("is_baseline", sa.Boolean(), nullable=False),
        sa.Column("baseline_key", sa.String(96), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "scope_kind IN ('organization', 'application', 'environment')",
            name="ck_policies_ck_policies_scope_kind",
        ),
        sa.CheckConstraint("phase IN ('input', 'output')", name="ck_policies_ck_policies_phase"),
        sa.CheckConstraint("priority >= 1", name="ck_policies_ck_policies_priority"),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name="ck_policies_ck_policies_status"
        ),
        sa.CheckConstraint(
            "(scope_kind = 'organization' AND scope_id = organization_id "
            "AND application_id IS NULL AND environment_id IS NULL) OR "
            "(scope_kind = 'application' AND scope_id = application_id "
            "AND application_id IS NOT NULL AND environment_id IS NULL) OR "
            "(scope_kind = 'environment' AND scope_id = environment_id "
            "AND application_id IS NOT NULL AND environment_id IS NOT NULL)",
            name="ck_policies_ck_policies_scope_shape",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
            name="fk_policies_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.application_id", "applications.organization_id"],
            ondelete="CASCADE",
            name="fk_policies_application_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "application_id", "organization_id"],
            [
                "environments.environment_id",
                "environments.application_id",
                "environments.organization_id",
            ],
            ondelete="CASCADE",
            name="fk_policies_environment_tenant",
        ),
        sa.PrimaryKeyConstraint("policy_id", name="pk_policies"),
        sa.UniqueConstraint("policy_id", "organization_id", name="uq_policies_id_organization"),
        sa.UniqueConstraint(
            "application_id", "baseline_key", name="uq_policies_application_baseline_key"
        ),
    )
    for column in ("organization_id", "application_id", "environment_id"):
        op.create_index(f"ix_policies_{column}", "policies", [column])
    op.create_index(
        "uq_policies_effective_priority",
        "policies",
        ["organization_id", "scope_kind", "scope_id", "phase", "priority"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
        sqlite_where=sa.text("archived_at IS NULL"),
    )
    op.create_index(
        "ix_policies_evaluation",
        "policies",
        ["organization_id", "scope_kind", "scope_id", "phase", "enabled", "priority"],
    )
    op.create_table(
        "policy_versions",
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("rationale_code", sa.String(96), nullable=False),
        sa.Column("condition_mode", sa.String(8), nullable=False),
        sa.Column("redaction_targets", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_policy_versions_ck_policy_versions_version"),
        sa.CheckConstraint(
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_policy_versions_ck_policy_versions_action",
        ),
        sa.CheckConstraint(
            "condition_mode IN ('all', 'any')",
            name="ck_policy_versions_ck_policy_versions_condition_mode",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "organization_id"],
            ["policies.policy_id", "policies.organization_id"],
            ondelete="CASCADE",
            name="fk_policy_versions_policy_tenant",
        ),
        sa.PrimaryKeyConstraint("policy_version_id", name="pk_policy_versions"),
        sa.UniqueConstraint("policy_id", "version", name="uq_policy_versions_number"),
    )
    op.create_index("ix_policy_versions_policy_id", "policy_versions", ["policy_id"])
    op.create_index("ix_policy_versions_organization_id", "policy_versions", ["organization_id"])
    op.create_index("ix_policy_versions_lookup", "policy_versions", ["policy_id", "version"])
    op.create_table(
        "policy_conditions",
        sa.Column("condition_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(48), nullable=False),
        sa.Column("operator", sa.String(32), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "ordinal BETWEEN 0 AND 19",
            name="ck_policy_conditions_ck_policy_conditions_ordinal",
        ),
        sa.ForeignKeyConstraint(
            ["policy_version_id"],
            ["policy_versions.policy_version_id"],
            ondelete="CASCADE",
            name="fk_policy_conditions_policy_version_id_policy_versions",
        ),
        sa.PrimaryKeyConstraint("condition_id", name="pk_policy_conditions"),
        sa.UniqueConstraint("policy_version_id", "ordinal", name="uq_policy_conditions_ordinal"),
    )
    op.create_index(
        "ix_policy_conditions_policy_version_id", "policy_conditions", ["policy_version_id"]
    )


def _extend_analysis_tables() -> None:
    with op.batch_alter_table("security_events") as batch:
        batch.add_column(sa.Column("action", sa.String(24), nullable=True))
        batch.add_column(sa.Column("risk_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("risk_severity", sa.String(16), nullable=True))
        batch.add_column(sa.Column("risk_profile_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("risk_profile_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("selected_policy_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("selected_policy_version_id", sa.Uuid(), nullable=True))
        batch.create_check_constraint(
            "ck_security_events_ck_security_events_action",
            "action IS NULL OR action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
        )
        batch.create_check_constraint(
            "ck_security_events_ck_security_events_risk_score",
            "risk_score IS NULL OR risk_score BETWEEN 0 AND 100",
        )
        batch.create_index("ix_security_events_action", ["action"])
        batch.create_index("ix_security_events_risk_severity", ["risk_severity"])

    with op.batch_alter_table("analysis_results") as batch:
        batch.add_column(sa.Column("risk_profile_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("risk_profile_version_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("risk_profile_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("risk_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("risk_severity", sa.String(16), nullable=True))
        batch.add_column(sa.Column("risk_confidence", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("base_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("corroboration_bonus", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("critical_floor", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("action", sa.String(24), nullable=True))
        batch.add_column(sa.Column("risk_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("policy_ms", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_analysis_results_risk_profile_id_risk_profiles",
            "risk_profiles",
            ["risk_profile_id"],
            ["risk_profile_id"],
        )
        batch.create_foreign_key(
            "fk_analysis_results_risk_profile_version",
            "risk_profile_versions",
            ["risk_profile_version_id"],
            ["risk_profile_version_id"],
        )
        batch.create_check_constraint(
            "ck_analysis_results_ck_analysis_results_risk_score",
            "risk_score BETWEEN 0 AND 100",
        )
        batch.create_check_constraint(
            "ck_analysis_results_ck_analysis_results_risk_confidence",
            "risk_confidence BETWEEN 0 AND 100",
        )
        batch.create_check_constraint(
            "ck_analysis_results_ck_analysis_results_risk_severity",
            "risk_severity IN ('low', 'medium', 'high', 'critical')",
        )
        batch.create_check_constraint(
            "ck_analysis_results_ck_analysis_results_action",
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
        )


def _create_evidence_tables() -> None:
    op.create_table(
        "risk_contributions",
        sa.Column("contribution_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("detector_id", sa.String(96), nullable=False),
        sa.Column("detector_version", sa.String(32), nullable=False),
        sa.Column("base_weight", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("raw_contribution", sa.Integer(), nullable=False),
        sa.Column("overlap_group", sa.String(96), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("suppressed_by_finding_id", sa.Uuid(), nullable=True),
        sa.Column("corroboration_bonus", sa.Integer(), nullable=False),
        sa.Column("critical_floor_applied", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "base_weight BETWEEN 0 AND 100",
            name="ck_risk_contributions_ck_risk_contributions_base",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name="ck_risk_contributions_ck_risk_contributions_confidence",
        ),
        sa.CheckConstraint(
            "raw_contribution BETWEEN 0 AND 100",
            name="ck_risk_contributions_ck_risk_contributions_raw",
        ),
        sa.CheckConstraint(
            "status IN ('retained', 'suppressed')",
            name="ck_risk_contributions_ck_risk_contributions_status",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analysis_results.analysis_id"],
            ondelete="CASCADE",
            name="fk_risk_contributions_analysis_id_analysis_results",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.finding_id"],
            ondelete="CASCADE",
            name="fk_risk_contributions_finding_id_findings",
        ),
        sa.ForeignKeyConstraint(
            ["suppressed_by_finding_id"],
            ["findings.finding_id"],
            name="fk_risk_contributions_suppressed_by_finding_id_findings",
        ),
        sa.PrimaryKeyConstraint("contribution_id", name="pk_risk_contributions"),
    )
    op.create_index("ix_risk_contributions_analysis_id", "risk_contributions", ["analysis_id"])
    op.create_index("ix_risk_contributions_finding_id", "risk_contributions", ["finding_id"])
    op.create_index(
        "ix_risk_contributions_analysis",
        "risk_contributions",
        ["analysis_id", "status"],
    )
    op.create_table(
        "policy_decisions",
        sa.Column("policy_decision_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("risk_profile_version_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("selected_policy_id", sa.Uuid(), nullable=True),
        sa.Column("selected_policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("scope_winners", sa.JSON(), nullable=False),
        sa.Column("evaluated_policy_versions", sa.JSON(), nullable=False),
        sa.Column("rationale_code", sa.String(96), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "phase IN ('input', 'output')",
            name="ck_policy_decisions_ck_policy_decisions_phase",
        ),
        sa.CheckConstraint(
            "action IN ('allow', 'flag', 'block', 'redact', 'require_review')",
            name="ck_policy_decisions_ck_policy_decisions_action",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analysis_results.analysis_id"],
            ondelete="CASCADE",
            name="fk_policy_decisions_analysis_id_analysis_results",
        ),
        sa.ForeignKeyConstraint(
            ["risk_profile_version_id"],
            ["risk_profile_versions.risk_profile_version_id"],
            name="fk_policy_decisions_risk_profile_version",
        ),
        sa.ForeignKeyConstraint(
            ["selected_policy_id"],
            ["policies.policy_id"],
            name="fk_policy_decisions_selected_policy_id_policies",
        ),
        sa.ForeignKeyConstraint(
            ["selected_policy_version_id"],
            ["policy_versions.policy_version_id"],
            name="fk_policy_decisions_selected_policy_version_id_policy_versions",
        ),
        sa.PrimaryKeyConstraint("policy_decision_id", name="pk_policy_decisions"),
        sa.UniqueConstraint("analysis_id", name="uq_policy_decisions_analysis_id"),
    )
    op.create_index("ix_policy_decisions_analysis", "policy_decisions", ["analysis_id"])


def _seed_profile_and_baselines() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)
    risk_profiles = sa.table(
        "risk_profiles",
        sa.column("risk_profile_id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("active_version", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("system_owned", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    versions = sa.table(
        "risk_profile_versions",
        sa.column("risk_profile_version_id", sa.Uuid()),
        sa.column("risk_profile_id", sa.Uuid()),
        sa.column("version", sa.Integer()),
        sa.column("weights", sa.JSON()),
        sa.column("thresholds", sa.JSON()),
        sa.column("formula_metadata", sa.JSON()),
        sa.column("formula_version", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("activated_at", sa.DateTime(timezone=True)),
    )
    bind.execute(
        risk_profiles.insert().values(
            risk_profile_id=PROFILE_ID,
            organization_id=None,
            name="renzai-v1",
            active_version=1,
            status="active",
            system_owned=True,
            created_at=now,
            updated_at=now,
        )
    )
    bind.execute(
        versions.insert().values(
            risk_profile_version_id=PROFILE_VERSION_ID,
            risk_profile_id=PROFILE_ID,
            version=1,
            weights=WEIGHTS,
            thresholds={"low": 0, "medium": 25, "high": 50, "critical": 75},
            formula_metadata={
                "rounding": "integer_half_up",
                "corroboration_cap": 25,
                "independent_contribution_limit": 2,
                "critical_output_secret_floor": 80,
            },
            formula_version="1.0.0",
            created_at=now,
            activated_at=now,
        )
    )
    _seed_application_baselines(bind, now)


def _seed_application_baselines(bind: sa.Connection, now: datetime) -> None:
    applications = sa.table(
        "applications",
        sa.column("application_id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
    )
    policies = sa.table(
        "policies",
        sa.column("policy_id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("application_id", sa.Uuid()),
        sa.column("environment_id", sa.Uuid()),
        sa.column("scope_kind", sa.String()),
        sa.column("scope_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("phase", sa.String()),
        sa.column("priority", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("active_version", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("is_baseline", sa.Boolean()),
        sa.column("baseline_key", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("archived_at", sa.DateTime(timezone=True)),
    )
    policy_versions = sa.table(
        "policy_versions",
        sa.column("policy_version_id", sa.Uuid()),
        sa.column("policy_id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("version", sa.Integer()),
        sa.column("action", sa.String()),
        sa.column("rationale_code", sa.String()),
        sa.column("condition_mode", sa.String()),
        sa.column("redaction_targets", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("activated_at", sa.DateTime(timezone=True)),
    )
    conditions = sa.table(
        "policy_conditions",
        sa.column("condition_id", sa.Uuid()),
        sa.column("policy_version_id", sa.Uuid()),
        sa.column("ordinal", sa.Integer()),
        sa.column("field", sa.String()),
        sa.column("operator", sa.String()),
        sa.column("value", sa.JSON()),
    )
    for application_id, organization_id in bind.execute(
        sa.select(applications.c.application_id, applications.c.organization_id)
    ):
        for key, name, phase, priority, action, match_value, targets in BASELINES:
            policy_id = uuid5(NAMESPACE_URL, f"renzai:{application_id}:{key}:policy")
            version_id = uuid5(NAMESPACE_URL, f"renzai:{application_id}:{key}:version:1")
            condition_id = uuid5(NAMESPACE_URL, f"renzai:{application_id}:{key}:condition:0")
            is_secret = key == "v1.output.secret_exposure"
            bind.execute(
                policies.insert().values(
                    policy_id=policy_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=None,
                    scope_kind="application",
                    scope_id=application_id,
                    name=name,
                    phase=phase,
                    priority=priority,
                    enabled=True,
                    active_version=1,
                    status="active",
                    is_baseline=True,
                    baseline_key=key,
                    created_at=now,
                    updated_at=now,
                    archived_at=None,
                )
            )
            bind.execute(
                policy_versions.insert().values(
                    policy_version_id=version_id,
                    policy_id=policy_id,
                    organization_id=organization_id,
                    version=1,
                    action=action,
                    rationale_code=(
                        "baseline_output_secret_redact"
                        if is_secret
                        else f"baseline_{phase}_{match_value}_{action}"
                    ),
                    condition_mode="all",
                    redaction_targets=list(targets),
                    created_at=now,
                    activated_at=now,
                )
            )
            bind.execute(
                conditions.insert().values(
                    condition_id=condition_id,
                    policy_version_id=version_id,
                    ordinal=0,
                    field="category_set" if is_secret else "severity",
                    operator="contains_category" if is_secret else "equals",
                    value=match_value,
                )
            )


def downgrade() -> None:
    op.drop_table("policy_decisions")
    op.drop_table("risk_contributions")
    with op.batch_alter_table("analysis_results") as batch:
        for name in (
            "ck_analysis_results_ck_analysis_results_action",
            "ck_analysis_results_ck_analysis_results_risk_severity",
            "ck_analysis_results_ck_analysis_results_risk_confidence",
            "ck_analysis_results_ck_analysis_results_risk_score",
        ):
            batch.drop_constraint(name, type_="check")
        batch.drop_constraint(
            "fk_analysis_results_risk_profile_version",
            type_="foreignkey",
        )
        batch.drop_constraint(
            "fk_analysis_results_risk_profile_id_risk_profiles", type_="foreignkey"
        )
        for name in (
            "policy_ms",
            "risk_ms",
            "action",
            "critical_floor",
            "corroboration_bonus",
            "base_score",
            "risk_confidence",
            "risk_severity",
            "risk_score",
            "risk_profile_version",
            "risk_profile_version_id",
            "risk_profile_id",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("security_events") as batch:
        batch.drop_constraint("ck_security_events_ck_security_events_risk_score", type_="check")
        batch.drop_constraint("ck_security_events_ck_security_events_action", type_="check")
        batch.drop_index("ix_security_events_risk_severity")
        batch.drop_index("ix_security_events_action")
        for name in (
            "selected_policy_version_id",
            "selected_policy_id",
            "risk_profile_version",
            "risk_profile_id",
            "risk_severity",
            "risk_score",
            "action",
        ):
            batch.drop_column(name)
    op.drop_table("policy_conditions")
    op.drop_table("policy_versions")
    op.drop_table("policies")
    op.drop_table("risk_profile_versions")
    op.drop_table("risk_profiles")
