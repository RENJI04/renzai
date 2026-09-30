"""Phase 5 identity HTTP endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    csrf_principal,
    current_principal,
    get_crypto,
    get_db,
    logout_principal,
    session_cookie_name,
    validate_same_origin,
)
from renzai.core.time import as_utc
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.auth.application import IdentityService
from renzai.modules.memberships.models import Membership
from renzai.modules.organizations.models import Organization

router = APIRouter(prefix="/auth", tags=["authentication"])


class CredentialsRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class TokenConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


def _service(request: Request, db: AsyncSession, crypto: IdentityCrypto) -> IdentityService:
    return IdentityService(
        db,
        crypto,
        request.app.state.settings.session,
        request.app.state.settings.identity,
        request.app.state.dependencies.auth_rate_limiter,
    )


def _source(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(request: Request, response: Response, value: str) -> None:
    settings = request.app.state.settings.session
    response.set_cookie(
        session_cookie_name(request),
        value,
        max_age=settings.absolute_hours * 3600,
        secure=settings.secure_cookie,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(
        session_cookie_name(request),
        secure=request.app.state.settings.session.secure_cookie,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: CredentialsRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    validate_same_origin(request)
    user, public = await _service(request, db, crypto).register(
        body.email, body.password, _source(request)
    )
    _set_session_cookie(request, response, public)
    return {"user": _user_view(user)}


@router.post("/login")
async def login(
    body: CredentialsRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    validate_same_origin(request)
    user, public = await _service(request, db, crypto).login(
        body.email, body.password, _source(request)
    )
    _set_session_cookie(request, response, public)
    return {"user": _user_view(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    principal: Annotated[Principal | None, Depends(logout_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> None:
    if principal is not None:
        await _service(request, db, crypto).logout(principal.session, principal.user)
    _clear_session_cookie(request, response)


@router.get("/session")
async def session_bootstrap(
    principal: Annotated[Principal, Depends(current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    memberships = (
        await db.execute(
            select(Membership, Organization)
            .join(Organization, Organization.organization_id == Membership.organization_id)
            .where(Membership.user_id == principal.user.user_id, Membership.status == "active")
        )
    ).tuples()
    return {
        "user": _user_view(principal.user),
        "csrf_token": crypto.csrf_token(principal.session_public),
        "session": {
            "idle_expires_at": as_utc(principal.session.idle_expires_at).isoformat(),
            "absolute_expires_at": as_utc(principal.session.absolute_expires_at).isoformat(),
            "privilege_version": principal.session.privilege_version,
        },
        "memberships": [
            {
                "organization_id": str(item.organization_id),
                "membership_id": str(item.membership_id),
                "role": item.role,
                "organization_name": organization.name,
                "organization_slug": organization.slug,
            }
            for item, organization in memberships
        ],
    }


@router.post("/password/change")
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(csrf_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, bool]:
    public = await _service(request, db, crypto).change_password(
        principal.user, principal.session, body.current_password, body.new_password
    )
    _set_session_cookie(request, response, public)
    return {"ok": True}


@router.post("/password/reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: EmailRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    validate_same_origin(request)
    token = await _service(request, db, crypto).request_password_reset(body.email, _source(request))
    result: dict[str, object] = {"accepted": True}
    if request.app.state.settings.app.environment.value in {"development", "test"} and token:
        result["development_token"] = token
    return result


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    body: ResetConfirmRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, bool]:
    validate_same_origin(request)
    await _service(request, db, crypto).confirm_password_reset(body.token, body.password)
    return {"ok": True}


@router.post("/email/verification/request", status_code=status.HTTP_202_ACCEPTED)
async def request_email_verification(
    request: Request,
    principal: Annotated[Principal, Depends(csrf_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    token = await _service(request, db, crypto).request_email_verification(principal.user)
    result: dict[str, object] = {"accepted": True}
    if request.app.state.settings.app.environment.value in {"development", "test"} and token:
        result["development_token"] = token
    return result


@router.post("/email/verification/confirm")
async def confirm_email_verification(
    body: TokenConfirmRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, bool]:
    validate_same_origin(request)
    await _service(request, db, crypto).confirm_email_verification(body.token)
    return {"ok": True}


def _user_view(user: object) -> dict[str, object]:
    return {
        "user_id": str(user.user_id),  # type: ignore[attr-defined]
        "email": user.email,  # type: ignore[attr-defined]
        "status": user.status,  # type: ignore[attr-defined]
        "email_verified": user.email_verified_at is not None,  # type: ignore[attr-defined]
    }
