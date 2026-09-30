"""Risk-profile persistence adapter for the pure risk engine."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.modules.risk.domain import (
    BASE_WEIGHTS,
    RISK_FORMULA_VERSION,
    RISK_PROFILE_NAME,
    RISK_PROFILE_VERSION,
    SYSTEM_RISK_PROFILE_ID,
    SYSTEM_RISK_PROFILE_VERSION_ID,
    RiskProfileSnapshot,
)
from renzai.modules.risk.models import RiskProfile, RiskProfileVersion
from renzai.modules.security.domain.types import Category


async def ensure_system_risk_profile(db: AsyncSession) -> RiskProfileSnapshot:
    profile_id = UUID(SYSTEM_RISK_PROFILE_ID)
    version_id = UUID(SYSTEM_RISK_PROFILE_VERSION_ID)
    row = await db.get(RiskProfile, profile_id)
    if row is None:
        row = RiskProfile(
            risk_profile_id=profile_id,
            organization_id=None,
            name=RISK_PROFILE_NAME,
            active_version=RISK_PROFILE_VERSION,
            status="active",
            system_owned=True,
        )
        db.add(row)
        db.add(
            RiskProfileVersion(
                risk_profile_version_id=version_id,
                risk_profile_id=profile_id,
                version=RISK_PROFILE_VERSION,
                weights={category.value: weight for category, weight in BASE_WEIGHTS.items()},
                thresholds={"low": 0, "medium": 25, "high": 50, "critical": 75},
                formula_metadata={
                    "rounding": "integer_half_up",
                    "corroboration_cap": 25,
                    "critical_secret_floor": 80,
                    "max_retained_groups": 2,
                },
                formula_version=RISK_FORMULA_VERSION,
            )
        )
        await db.flush()
    version = (
        await db.execute(
            select(RiskProfileVersion).where(
                RiskProfileVersion.risk_profile_id == profile_id,
                RiskProfileVersion.version == row.active_version,
            )
        )
    ).scalar_one()
    return RiskProfileSnapshot(
        profile_id=str(row.risk_profile_id),
        version_id=str(version.risk_profile_version_id),
        name=row.name,
        version=version.version,
        formula_version=version.formula_version,
        weights={Category(name): int(weight) for name, weight in version.weights.items()},
    )
