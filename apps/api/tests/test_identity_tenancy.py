from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.app import create_app
from renzai.core.config import Environment, Settings
from renzai.core.errors import RateLimitError
from renzai.core.time import utc_now
from renzai.db import models as _models  # noqa: F401
from renzai.db.base import Base
from renzai.db.session import Database
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.audit.models import AuditEvent
from renzai.modules.auth.models import Session
from renzai.modules.auth.rate_limit import InMemoryAuthRateLimiter
from renzai.modules.memberships.domain import MembershipRole, can_assign_role
from renzai.modules.users.models import User


@pytest.fixture
def identity_client(tmp_path: Path) -> Iterator[tuple[TestClient, Settings]]:
    database_path = tmp_path / "identity.sqlite3"
    settings = Settings(
        app_environment=Environment.TEST,
        app_public_base_url="http://testserver",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        session_secure_cookie=False,
        auth_rate_limit_attempts=100,
    )

    async def create_schema() -> None:
        database = Database(settings.database)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await database.close()

    asyncio.run(create_schema())
    with TestClient(create_app(settings), base_url="http://testserver") as client:
        yield client, settings


def register(client: TestClient, email: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct horse 12345"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def run_db[T](settings: Settings, operation: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def execute() -> T:
        database = Database(settings.database)
        async with database.session() as session:
            result = await operation(session)
            await session.commit()
        await database.close()
        return result

    return asyncio.run(execute())


@pytest.mark.e2e
def test_registration_session_logout_and_csrf(identity_client: tuple[TestClient, Settings]) -> None:
    client, _ = identity_client
    body = register(client, " Alice@Example.COM ")
    assert body["user"]["email"] == "Alice@Example.COM"
    token = csrf(client)
    cookie = client.cookies.get("renzai_session")
    assert cookie and cookie not in str(body)

    rejected = client.post("/api/v1/auth/logout")
    assert rejected.status_code == 403
    assert rejected.json()["error"]["details"]["reason"] == "csrf"

    response = client.post("/api/v1/auth/logout", headers={"X-Renzai-CSRF": token})
    assert response.status_code == 204
    assert client.post("/api/v1/auth/logout", headers={"X-Renzai-CSRF": token}).status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401


def test_login_is_generic_and_duplicate_email_conflicts(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, _ = identity_client
    register(client, "alice@example.com")
    client.cookies.clear()
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "ALICE@example.com", "password": "correct horse 12345"},
    )
    assert duplicate.status_code == 409
    failed = client.post(
        "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong"}
    )
    assert failed.status_code == 401
    assert failed.json()["error"]["message"] == "Authentication is required."


@pytest.mark.e2e
def test_password_reset_is_single_use_and_revokes_sessions(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, _ = identity_client
    register(client, "alice@example.com")
    response = client.post(
        "/api/v1/auth/password/reset/request", json={"email": "alice@example.com"}
    )
    assert response.status_code == 202
    replaced_token = response.json()["development_token"]
    response = client.post(
        "/api/v1/auth/password/reset/request", json={"email": "alice@example.com"}
    )
    token = response.json()["development_token"]
    assert (
        client.post(
            "/api/v1/auth/password/reset/confirm",
            json={"token": replaced_token, "password": "a new password 67890"},
        ).status_code
        == 401
    )
    confirmation = {"token": token, "password": "a new password 67890"}
    assert client.post("/api/v1/auth/password/reset/confirm", json=confirmation).status_code == 200
    assert client.post("/api/v1/auth/password/reset/confirm", json=confirmation).status_code == 401
    assert client.get("/api/v1/auth/session").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "a new password 67890"},
        ).status_code
        == 200
    )


@pytest.mark.e2e
def test_password_change_rotates_current_and_revokes_other_sessions(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, settings = identity_client
    register(client, "alice@example.com")
    old_cookie = client.cookies.get("renzai_session")
    with TestClient(create_app(settings), base_url="http://testserver") as other_client:
        login = other_client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "correct horse 12345"},
        )
        assert login.status_code == 200
        changed = client.post(
            "/api/v1/auth/password/change",
            headers={"X-Renzai-CSRF": csrf(client)},
            json={
                "current_password": "correct horse 12345",
                "new_password": "replacement password 67890",
            },
        )
        assert changed.status_code == 200
        assert client.cookies.get("renzai_session") != old_cookie
        assert client.get("/api/v1/auth/session").status_code == 200
        assert other_client.get("/api/v1/auth/session").status_code == 401


def test_org_invitation_rbac_cross_tenant_and_last_owner(
    identity_client: tuple[TestClient, Settings],
) -> None:
    owner_client, settings = identity_client
    register(owner_client, "owner@example.com")
    owner_csrf = csrf(owner_client)
    created = owner_client.post(
        "/api/v1/organizations",
        headers={"X-Renzai-CSRF": owner_csrf},
        json={"name": "Acme Security", "slug": "acme-security"},
    )
    assert created.status_code == 201, created.text
    organization = created.json()
    org_id = organization["organization_id"]
    assert organization["settings"]["audit_retention_days"] == 365
    updated = owner_client.patch(
        f"/api/v1/organizations/{org_id}",
        headers={"X-Renzai-CSRF": owner_csrf},
        json={"audit_retention_days": 730},
    )
    assert updated.status_code == 200
    assert updated.json()["settings"]["audit_retention_days"] == 730

    cannot_remove_last = owner_client.delete(
        f"/api/v1/organizations/{org_id}/members/{organization['membership_id']}",
        headers={"X-Renzai-CSRF": owner_csrf},
    )
    assert cannot_remove_last.status_code == 409
    assert cannot_remove_last.json()["error"]["details"]["reason"] == "last_owner"

    invitation = owner_client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        headers={"X-Renzai-CSRF": owner_csrf},
        json={"email": "member@example.com", "role": "viewer"},
    )
    assert invitation.status_code == 201
    replaced_token = invitation.json()["development_token"]
    invitation = owner_client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        headers={"X-Renzai-CSRF": owner_csrf},
        json={"email": "member@example.com", "role": "viewer"},
    )
    assert invitation.status_code == 201

    with TestClient(create_app(settings), base_url="http://testserver") as member_client:
        register(member_client, "member@example.com")
        member_csrf = csrf(member_client)
        assert (
            member_client.post(
                f"/api/v1/invitations/{replaced_token}/accept",
                headers={"X-Renzai-CSRF": member_csrf},
            ).status_code
            == 404
        )
        accepted = member_client.post(
            f"/api/v1/invitations/{invitation.json()['development_token']}/accept",
            headers={"X-Renzai-CSRF": member_csrf},
        )
        assert accepted.status_code == 200, accepted.text
        assert member_client.get(f"/api/v1/organizations/{org_id}").status_code == 200
        assert (
            member_client.post(
                f"/api/v1/organizations/{org_id}/invitations",
                headers={"X-Renzai-CSRF": member_csrf},
                json={"email": "third@example.com", "role": "viewer"},
            ).status_code
            == 403
        )

        other = member_client.post(
            "/api/v1/organizations",
            headers={"X-Renzai-CSRF": member_csrf},
            json={"name": "Other Tenant", "slug": "other-tenant"},
        ).json()
        owner_client_response = owner_client.get(
            f"/api/v1/organizations/{other['organization_id']}"
        )
        assert owner_client_response.status_code == 404
        assert owner_client_response.json()["error"]["code"] == "not_found_or_hidden"

        changed = owner_client.patch(
            f"/api/v1/organizations/{org_id}/members/{accepted.json()['membership_id']}",
            headers={"X-Renzai-CSRF": owner_csrf},
            json={"role": "developer"},
        )
        assert changed.status_code == 200
        assert member_client.get("/api/v1/auth/session").status_code == 401


def test_origin_is_enforced_when_browser_header_is_present(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, _ = identity_client
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "https://attacker.example"},
        json={"email": "alice@example.com", "password": "correct horse 12345"},
    )
    assert response.status_code == 403


def test_email_verification_is_single_use(identity_client: tuple[TestClient, Settings]) -> None:
    client, _ = identity_client
    register(client, "alice@example.com")
    requested = client.post(
        "/api/v1/auth/email/verification/request", headers={"X-Renzai-CSRF": csrf(client)}
    )
    replaced_token = requested.json()["development_token"]
    requested = client.post(
        "/api/v1/auth/email/verification/request", headers={"X-Renzai-CSRF": csrf(client)}
    )
    verification = requested.json()["development_token"]
    assert (
        client.post(
            "/api/v1/auth/email/verification/confirm", json={"token": replaced_token}
        ).status_code
        == 401
    )
    payload = {"token": verification}
    assert client.post("/api/v1/auth/email/verification/confirm", json=payload).status_code == 200
    assert client.post("/api/v1/auth/email/verification/confirm", json=payload).status_code == 401
    assert client.get("/api/v1/auth/session").json()["user"]["email_verified"] is True


def test_disabled_and_expired_sessions_are_rejected(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, settings = identity_client
    registered = register(client, "alice@example.com")
    user_id = registered["user"]["user_id"]
    session_cookie = client.cookies.get("renzai_session")
    assert session_cookie is not None

    async def disable(session: AsyncSession) -> None:
        user = await session.get(User, UUID(user_id))
        assert user is not None
        user.status = "disabled"

    run_db(settings, disable)
    assert client.get("/api/v1/auth/session").status_code == 401
    assert client.cookies.get("renzai_session") is None

    async def reactivate_and_expire(session: AsyncSession) -> None:
        user = await session.get(User, UUID(user_id))
        assert user is not None
        user.status = "active"
        active_session = (
            await session.execute(select(Session).where(Session.user_id == user.user_id))
        ).scalar_one()
        active_session.idle_expires_at = utc_now() - timedelta(seconds=1)

    run_db(settings, reactivate_and_expire)
    client.cookies.set("renzai_session", session_cookie)
    assert client.get("/api/v1/auth/session").status_code == 401

    async def expire_absolute(session: AsyncSession) -> None:
        active_session = (await session.execute(select(Session))).scalar_one()
        active_session.idle_expires_at = utc_now() + timedelta(minutes=5)
        active_session.absolute_expires_at = utc_now() - timedelta(seconds=1)

    run_db(settings, expire_absolute)
    client.cookies.set("renzai_session", session_cookie)
    assert client.get("/api/v1/auth/session").status_code == 401


def test_tenant_actions_create_tenant_scoped_audit_records(
    identity_client: tuple[TestClient, Settings],
) -> None:
    client, settings = identity_client
    register(client, "owner@example.com")
    created = client.post(
        "/api/v1/organizations",
        headers={"X-Renzai-CSRF": csrf(client)},
        json={"name": "Audit Tenant", "slug": "audit-tenant"},
    ).json()

    async def load_events(session: AsyncSession) -> list[AuditEvent]:
        result = await session.execute(
            select(AuditEvent).where(AuditEvent.organization_id == UUID(created["organization_id"]))
        )
        return list(result.scalars())

    events = run_db(settings, load_events)
    assert events[0].action == "organization.created"
    assert events[0].organization_id is not None


@pytest.mark.asyncio
async def test_auth_rate_limit_enforces_fixed_window() -> None:
    limiter = InMemoryAuthRateLimiter(attempts=2, window_seconds=60)
    await limiter.check("bucket")
    await limiter.check("bucket")
    with pytest.raises(RateLimitError):
        await limiter.check("bucket")


def test_crypto_stores_verifiers_not_public_secrets() -> None:
    crypto = IdentityCrypto("a-development-test-key-that-is-long", "v1")
    credential = crypto.create_credential("session")
    assert credential.public.encode() not in credential.verifier
    assert crypto.parse_and_verify(
        credential.public, "session", credential.lookup, credential.verifier
    )
    assert not crypto.parse_and_verify(
        credential.public + "x", "session", credential.lookup, credential.verifier
    )


def test_role_assignment_policy() -> None:
    assert can_assign_role(MembershipRole.OWNER, MembershipRole.OWNER)
    assert can_assign_role(MembershipRole.ADMIN, MembershipRole.DEVELOPER)
    assert not can_assign_role(MembershipRole.ADMIN, MembershipRole.OWNER)
    assert not can_assign_role(MembershipRole.VIEWER, MembershipRole.VIEWER)
