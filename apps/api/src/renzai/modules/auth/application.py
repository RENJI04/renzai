"""Identity use cases over explicit SQLAlchemy transaction boundaries."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.config import IdentityConfig, SessionConfig
from renzai.core.errors import AuthenticationError, ConflictError, ValidationError
from renzai.core.request_context import get_request_id
from renzai.core.time import as_utc, utc_now
from renzai.infrastructure.crypto.identity import IdentityCrypto, OpaqueCredential
from renzai.modules.audit.models import AccountSecurityEvent
from renzai.modules.auth.models import EmailVerificationToken, PasswordResetToken, Session
from renzai.modules.auth.ports import IdentityTokenDelivery
from renzai.modules.users.domain import UserStatus, normalize_email, validate_password
from renzai.modules.users.models import PasswordCredential, User


class AuthRateLimiter(Protocol):
    async def check(self, bucket: str) -> None: ...


class IdentityService:
    def __init__(
        self,
        db: AsyncSession,
        crypto: IdentityCrypto,
        session_config: SessionConfig,
        identity_config: IdentityConfig,
        rate_limiter: AuthRateLimiter,
        token_delivery: IdentityTokenDelivery | None = None,
    ) -> None:
        self.db = db
        self.crypto = crypto
        self.session_config = session_config
        self.identity_config = identity_config
        self.rate_limiter = rate_limiter
        self.token_delivery = token_delivery

    async def register(self, email: str, password: str, source: str) -> tuple[User, str]:
        normalized = normalize_email(email)
        validate_password(password)
        await self._rate_limit("register", normalized, source)
        try:
            user = User(email=email.strip(), normalized_email=normalized, status=UserStatus.ACTIVE)
            self.db.add(user)
            await self.db.flush()
            self.db.add(
                PasswordCredential(
                    user_id=user.user_id, password_hash=self.crypto.hash_password(password)
                )
            )
            public = await self._new_session(user)
            self._event(user.user_id, "auth.register", "success")
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": ["email"]}) from error
        return user, public

    async def login(self, email: str, password: str, source: str) -> tuple[User, str]:
        try:
            normalized = normalize_email(email)
        except ValidationError:
            normalized = "invalid"
        await self._rate_limit("login", normalized, source)
        row = (
            await self.db.execute(
                select(User, PasswordCredential)
                .join(PasswordCredential, PasswordCredential.user_id == User.user_id)
                .where(User.normalized_email == normalized)
            )
        ).one_or_none()
        if row is None:
            self.crypto.consume_dummy_password_check(password)
            self._event(None, "auth.login", "failure")
            await self.db.commit()
            raise AuthenticationError()
        user, credential = row
        valid, replacement = self.crypto.verify_password(credential.password_hash, password)
        if not valid or user.status != UserStatus.ACTIVE:
            self._event(user.user_id, "auth.login", "failure")
            await self.db.commit()
            raise AuthenticationError()
        if replacement:
            credential.password_hash = replacement
            credential.changed_at = utc_now()
        public = await self._new_session(user)
        self._event(user.user_id, "auth.login", "success")
        await self.db.commit()
        return user, public

    async def logout(self, session: Session, user: User) -> None:
        session.revoked_at = utc_now()
        self._event(user.user_id, "auth.logout", "success")
        await self.db.commit()

    async def change_password(
        self, user: User, current_session: Session, current_password: str, new_password: str
    ) -> str:
        validate_password(new_password)
        credential = (
            await self.db.execute(
                select(PasswordCredential).where(PasswordCredential.user_id == user.user_id)
            )
        ).scalar_one()
        valid, _ = self.crypto.verify_password(credential.password_hash, current_password)
        if not valid:
            raise AuthenticationError()
        credential.password_hash = self.crypto.hash_password(new_password)
        credential.changed_at = utc_now()
        user.privilege_version += 1
        await self.db.execute(
            update(Session)
            .where(Session.user_id == user.user_id, Session.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        public = await self._new_session(user)
        self._event(user.user_id, "auth.password.changed", "success")
        await self.db.commit()
        return public

    async def request_password_reset(self, email: str, source: str) -> str | None:
        try:
            normalized = normalize_email(email)
        except ValidationError:
            normalized = "invalid"
        await self._rate_limit("password-reset", normalized, source)
        user = (
            await self.db.execute(select(User).where(User.normalized_email == normalized))
        ).scalar_one_or_none()
        public: str | None = None
        if user is not None and user.status == UserStatus.ACTIVE:
            now = utc_now()
            await self.db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.user_id,
                    PasswordResetToken.used_at.is_(None),
                )
                .values(used_at=now)
            )
            token = self.crypto.create_credential("password-reset", "rzrt_")
            self.db.add(
                PasswordResetToken(
                    user_id=user.user_id,
                    lookup=token.lookup,
                    verifier=token.verifier,
                    verifier_key_id=self.crypto.key_id,
                    expires_at=now + timedelta(minutes=self.identity_config.password_reset_minutes),
                )
            )
            public = token.public
            self._event(user.user_id, "auth.password_reset.requested", "accepted")
        await self.db.commit()
        if public is not None and user is not None and self.token_delivery is not None:
            await self.token_delivery.send_password_reset(user.email, public)
        return public

    async def confirm_password_reset(self, token: str, password: str) -> None:
        validate_password(password)
        lookup = self.crypto.lookup(token, "rzrt_")
        if lookup is None:
            raise AuthenticationError()
        reset = (
            await self.db.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.lookup == lookup)
                .with_for_update()
            )
        ).scalar_one_or_none()
        now = utc_now()
        if (
            reset is None
            or reset.used_at is not None
            or as_utc(reset.expires_at) <= now
            or not self.crypto.parse_and_verify(
                token, "password-reset", reset.lookup, reset.verifier, "rzrt_"
            )
        ):
            raise AuthenticationError()
        credential = (
            await self.db.execute(
                select(PasswordCredential).where(PasswordCredential.user_id == reset.user_id)
            )
        ).scalar_one()
        user = await self.db.get(User, reset.user_id)
        if user is None:
            raise AuthenticationError()
        credential.password_hash = self.crypto.hash_password(password)
        credential.changed_at = now
        await self.db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        user.privilege_version += 1
        await self.db.execute(
            update(Session)
            .where(Session.user_id == user.user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        self._event(user.user_id, "auth.password_reset.confirmed", "success")
        await self.db.commit()

    async def request_email_verification(self, user: User) -> str | None:
        if user.email_verified_at is not None:
            return None
        now = utc_now()
        await self.db.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        token = self.crypto.create_credential("email-verification", "rzvt_")
        self.db.add(
            EmailVerificationToken(
                user_id=user.user_id,
                lookup=token.lookup,
                verifier=token.verifier,
                verifier_key_id=self.crypto.key_id,
                expires_at=now + timedelta(hours=self.identity_config.email_verification_hours),
            )
        )
        self._event(user.user_id, "auth.email_verification.requested", "accepted")
        await self.db.commit()
        if self.token_delivery is not None:
            await self.token_delivery.send_email_verification(user.email, token.public)
        return token.public

    async def confirm_email_verification(self, token: str) -> None:
        lookup = self.crypto.lookup(token, "rzvt_")
        if lookup is None:
            raise AuthenticationError()
        verification = (
            await self.db.execute(
                select(EmailVerificationToken)
                .where(EmailVerificationToken.lookup == lookup)
                .with_for_update()
            )
        ).scalar_one_or_none()
        now = utc_now()
        if (
            verification is None
            or verification.used_at is not None
            or as_utc(verification.expires_at) <= now
            or not self.crypto.parse_and_verify(
                token,
                "email-verification",
                verification.lookup,
                verification.verifier,
                "rzvt_",
            )
        ):
            raise AuthenticationError()
        user = await self.db.get(User, verification.user_id)
        if user is None:
            raise AuthenticationError()
        user.email_verified_at = now
        verification.used_at = now
        self._event(user.user_id, "auth.email_verification.confirmed", "success")
        await self.db.commit()

    async def _new_session(self, user: User) -> str:
        credential: OpaqueCredential = self.crypto.create_credential("session")
        now = utc_now()
        csrf = self.crypto.csrf_token(credential.public)
        self.db.add(
            Session(
                user_id=user.user_id,
                lookup=credential.lookup,
                verifier=credential.verifier,
                verifier_key_id=self.crypto.key_id,
                csrf_verifier=self.crypto.csrf_verifier(credential.lookup, csrf),
                privilege_version=user.privilege_version,
                idle_expires_at=now + timedelta(minutes=self.session_config.idle_minutes),
                absolute_expires_at=now + timedelta(hours=self.session_config.absolute_hours),
            )
        )
        return credential.public

    async def _rate_limit(self, operation: str, identity: str, source: str) -> None:
        key = self.crypto.rate_limit_identifier(f"{operation}:{identity}:{source}")
        await self.rate_limiter.check(key)

    def _event(self, user_id: UUID | None, action: str, outcome: str) -> None:
        self.db.add(
            AccountSecurityEvent(
                user_id=user_id,
                action=action,
                outcome=outcome,
                request_id=get_request_id(),
                safe_metadata={},
            )
        )
