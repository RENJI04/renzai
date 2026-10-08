from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from renzai.db import models as _models  # noqa: F401 - registers all tables
from renzai.db.base import Base
from renzai.demo import (
    DEMO_MARKER,
    DEMO_ORGANIZATION_SLUG,
    DemoSafetyError,
    reset_demo,
    seed_demo,
)
from renzai.modules.applications.models import Application
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.organizations.models import Organization
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.security.models import AnalysisResult, SecurityEvent
from renzai.modules.users.models import PasswordCredential, User


@pytest.mark.asyncio
async def test_demo_seed_reset_seed_is_bounded_and_reproducible() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with sessions() as session:
            owner = User(
                email="analyst@demo.invalid",
                normalized_email="analyst@demo.invalid",
                status="active",
                email_verified_at=datetime(2026, 10, 7, tzinfo=UTC),
            )
            unrelated = Organization(
                name="Unrelated tenant",
                slug="unrelated-tenant",
                settings={},
            )
            session.add_all([owner, unrelated])
            await session.commit()

            first = await seed_demo(
                session,
                now=datetime(2026, 10, 7, 8, tzinfo=UTC),
            )
            duplicate = await seed_demo(session)
            assert duplicate.already_present is True
            assert duplicate.applications == first.applications == 3
            assert duplicate.environments == first.environments == 9
            assert duplicate.analyses == first.analyses == 28
            assert duplicate.incidents == first.incidents == 8
            assert duplicate.provider_calls == first.provider_calls == 8
            assert duplicate.ai_results == first.ai_results == 1
            assert await session.scalar(select(func.count()).select_from(PasswordCredential)) == 0
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(ProviderConfiguration)
                    .where(ProviderConfiguration.credential_ciphertext.is_not(None))
                )
                == 0
            )
            gateway_links = (
                await session.execute(
                    select(GatewayProviderCall, ProviderConfiguration, SecurityEvent)
                    .join(
                        ProviderConfiguration,
                        ProviderConfiguration.provider_id == GatewayProviderCall.provider_id,
                    )
                    .join(
                        AnalysisResult,
                        AnalysisResult.analysis_id == GatewayProviderCall.input_analysis_id,
                    )
                    .join(SecurityEvent, SecurityEvent.event_id == AnalysisResult.event_id)
                )
            ).all()
            assert len(gateway_links) == 8
            assert all(
                call.application_id == provider.application_id == event.application_id
                and call.environment_id == provider.environment_id == event.environment_id
                for call, provider, event in gateway_links
            )

            assert await reset_demo(session) is True
            assert await reset_demo(session) is False
            assert (
                await session.scalar(
                    select(Organization).where(Organization.slug == "unrelated-tenant")
                )
                is not None
            )
            assert await session.scalar(select(func.count()).select_from(Application)) == 0

            session.expunge_all()
            second = await seed_demo(
                session,
                now=datetime(2026, 10, 7, 8, tzinfo=UTC),
            )
            assert second == first
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_demo_operations_refuse_ambiguous_or_personal_targets() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with sessions() as session:
            session.add(
                Organization(
                    name="Not demo data",
                    slug=DEMO_ORGANIZATION_SLUG,
                    settings={"demo_dataset": f"{DEMO_MARKER}-wrong"},
                )
            )
            await session.commit()
            with pytest.raises(DemoSafetyError, match="reserved slug"):
                await reset_demo(session)
            with pytest.raises(DemoSafetyError, match="reserved @demo.invalid"):
                await seed_demo(session, owner_email="person@example.org")
    finally:
        await engine.dispose()
