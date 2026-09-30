"""Request-scoped database, authentication, CSRF, and tenant dependencies."""

from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import AuthenticationError, AuthorizationError, NotFoundOrHiddenError
from renzai.core.request_context import get_request_id
from renzai.core.time import as_utc, utc_now
from renzai.infrastructure.crypto.application_keys import ENVIRONMENT_TAGS, ApplicationKeyCrypto
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.api_keys.models import ApplicationApiKey
from renzai.modules.applications.models import Application
from renzai.modules.auth.models import Session
from renzai.modules.environments.models import Environment as ApplicationEnvironment
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.users.domain import UserStatus
from renzai.modules.users.models import User


@dataclass(frozen=True, slots=True)
class Principal:
    user: User
    session: Session
    session_public: str


@dataclass(frozen=True, slots=True)
class TenantPrincipal:
    principal: Principal
    membership: Membership
    organization_id: UUID
    role: MembershipRole
    privilege_version: int
    request_id: str | None


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    organization_id: UUID
    application_id: UUID
    environment_id: UUID
    key_id: UUID
    correlation_id: str
    application: Application
    environment: ApplicationEnvironment


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.dependencies.database.session() as session:
        yield session


def get_crypto(request: Request) -> IdentityCrypto:
    return request.app.state.dependencies.identity_crypto  # type: ignore[no-any-return]


def get_application_key_crypto(request: Request) -> ApplicationKeyCrypto:
    return request.app.state.dependencies.application_key_crypto  # type: ignore[no-any-return]


def session_cookie_name(request: Request) -> str:
    if request.app.state.settings.session.secure_cookie:
        return "__Host-renzai_session"
    return "renzai_session"


def validate_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    expected = str(request.app.state.settings.app.public_base_url).rstrip("/")
    candidate = origin or referer
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise AuthorizationError(details={"reason": "origin"})
    if candidate is None:
        return
    expected_url = urlsplit(expected)
    candidate_url = urlsplit(candidate)
    if (candidate_url.scheme, candidate_url.netloc) != (expected_url.scheme, expected_url.netloc):
        raise AuthorizationError(details={"reason": "origin"})


async def current_principal(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> Principal:
    public = request.cookies.get(session_cookie_name(request))
    lookup = crypto.lookup(public or "")
    if not public or not lookup:
        if public:
            request.state.clear_session_cookie = True
        raise AuthenticationError()
    row = (
        await db.execute(
            select(Session, User)
            .join(User, User.user_id == Session.user_id)
            .where(Session.lookup == lookup)
        )
    ).one_or_none()
    if row is None:
        request.state.clear_session_cookie = True
        raise AuthenticationError()
    session, user = row
    now = utc_now()
    valid = (
        session.revoked_at is None
        and user.status == UserStatus.ACTIVE
        and session.privilege_version == user.privilege_version
        and as_utc(session.idle_expires_at) > now
        and as_utc(session.absolute_expires_at) > now
        and crypto.parse_and_verify(public, "session", session.lookup, session.verifier)
    )
    if not valid:
        request.state.clear_session_cookie = True
        raise AuthenticationError()
    session.last_seen_at = now
    session.idle_expires_at = min(
        now + request.app.state.identity_idle_delta, as_utc(session.absolute_expires_at)
    )
    await db.commit()
    return Principal(user=user, session=session, session_public=public)


async def csrf_principal(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> Principal:
    validate_same_origin(request)
    supplied = request.headers.get("X-Renzai-CSRF", "")
    if len(supplied) > 128:
        raise AuthorizationError(details={"reason": "csrf"})
    expected = crypto.csrf_verifier(principal.session.lookup, supplied)
    if not supplied or not hmac.compare_digest(expected, principal.session.csrf_verifier):
        raise AuthorizationError(details={"reason": "csrf"})
    return principal


async def logout_principal(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> Principal | None:
    """Authenticate a live logout, but let an already-cleared/revoked session converge."""
    validate_same_origin(request)
    public = request.cookies.get(session_cookie_name(request))
    lookup = crypto.lookup(public or "")
    if not public or not lookup:
        return None
    row = (
        await db.execute(
            select(Session, User)
            .join(User, User.user_id == Session.user_id)
            .where(Session.lookup == lookup)
        )
    ).one_or_none()
    if row is None:
        return None
    session, user = row
    now = utc_now()
    if not (
        session.revoked_at is None
        and user.status == UserStatus.ACTIVE
        and session.privilege_version == user.privilege_version
        and as_utc(session.idle_expires_at) > now
        and as_utc(session.absolute_expires_at) > now
        and crypto.parse_and_verify(public, "session", session.lookup, session.verifier)
    ):
        return None
    supplied = request.headers.get("X-Renzai-CSRF", "")
    if (
        not supplied
        or len(supplied) > 128
        or not hmac.compare_digest(
            crypto.csrf_verifier(session.lookup, supplied), session.csrf_verifier
        )
    ):
        raise AuthorizationError(details={"reason": "csrf"})
    return Principal(user=user, session=session, session_public=public)


async def tenant_principal(
    request: Request,
    organization_id: UUID,
    principal: Annotated[Principal, Depends(current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantPrincipal:
    if (
        request.app.state.settings.identity.email_verification_required
        and principal.user.email_verified_at is None
    ):
        raise AuthorizationError(details={"reason": "email_verification_required"})
    membership = (
        await db.execute(
            select(Membership).where(
                Membership.organization_id == organization_id,
                Membership.user_id == principal.user.user_id,
                Membership.status == "active",
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise NotFoundOrHiddenError()
    return TenantPrincipal(
        principal=principal,
        membership=membership,
        organization_id=organization_id,
        role=MembershipRole(membership.role),
        privilege_version=principal.user.privilege_version,
        request_id=get_request_id(),
    )


def require_member_manager(tenant: TenantPrincipal) -> None:
    if MembershipRole(tenant.membership.role) not in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        raise AuthorizationError()


async def application_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> ApplicationContext:
    authorization = request.headers.get("authorization", "")
    scheme, _, public = authorization.partition(" ")
    parsed = crypto.parse(public) if scheme.lower() == "bearer" else None
    if parsed is None:
        # Consume equivalent keyed work for malformed credentials without retaining input.
        crypto.verifier("A" * 22, "B" * 43)
        raise AuthenticationError()
    row = (
        await db.execute(
            select(ApplicationApiKey, ApplicationEnvironment, Application)
            .join(
                ApplicationEnvironment,
                ApplicationEnvironment.environment_id == ApplicationApiKey.environment_id,
            )
            .join(Application, Application.application_id == ApplicationApiKey.application_id)
            .where(ApplicationApiKey.lookup == parsed.lookup)
        )
    ).one_or_none()
    if row is None:
        crypto.verifier(parsed.lookup, parsed.secret)
        raise AuthenticationError()
    key, environment, application = row
    now = utc_now()
    valid = (
        key.revoked_at is None
        and (key.expires_at is None or as_utc(key.expires_at) > now)
        and application.status == "active"
        and environment.status == "active"
        and key.organization_id == application.organization_id == environment.organization_id
        and key.application_id == application.application_id == environment.application_id
        and key.environment_id == environment.environment_id
        and parsed.environment_tag == ENVIRONMENT_TAGS.get(environment.type)
        and key.verifier_key_id == crypto.key_id
        and crypto.verify(public, key.lookup, key.verifier)
    )
    if not valid:
        raise AuthenticationError()
    # Keep successful last-use writes bounded to at most once per minute.
    if key.last_used_at is None or as_utc(key.last_used_at) < now - timedelta(minutes=1):
        key.last_used_at = now
        await db.commit()
    return ApplicationContext(
        organization_id=key.organization_id,
        application_id=key.application_id,
        environment_id=key.environment_id,
        key_id=key.key_id,
        correlation_id=get_request_id() or "unknown",
        application=application,
        environment=environment,
    )
