"""Application, environment and application-key use cases."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.config import PrivacyMode
from renzai.core.errors import AuthorizationError, ConflictError, NotFoundOrHiddenError
from renzai.core.ids import new_uuid7
from renzai.core.request_context import get_request_id
from renzai.core.time import as_utc, utc_now
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.modules.api_keys.models import ApplicationApiKey
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AuditEvent
from renzai.modules.environments.models import Environment
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.users.models import User

APP_EDITORS = {MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.DEVELOPER}
OPERATORS = {MembershipRole.OWNER, MembershipRole.ADMIN}
ENVIRONMENT_TYPES = {"development", "staging", "production"}


class ApplicationService:
    def __init__(
        self,
        db: AsyncSession,
        key_crypto: ApplicationKeyCrypto,
        default_privacy_mode: PrivacyMode,
        default_safe_persistence: bool,
        default_retention_days: int,
        maximum_key_expiry_days: int,
    ) -> None:
        self.db = db
        self.key_crypto = key_crypto
        self.default_privacy_mode = default_privacy_mode
        self.default_safe_persistence = default_safe_persistence
        self.default_retention_days = default_retention_days
        self.maximum_key_expiry_days = maximum_key_expiry_days

    async def create_application(
        self, actor: Membership, user: User, name: str, *, commit: bool = True
    ) -> Application:
        self._require_editor(actor)
        clean_name = self._name(name)
        application = Application(
            application_id=new_uuid7(),
            organization_id=actor.organization_id,
            name=clean_name,
            name_key=clean_name.casefold(),
            privacy_mode=self.default_privacy_mode.value,
            safe_content_persistence=self.default_safe_persistence,
            security_retention_days=self.default_retention_days,
        )
        self.db.add(application)
        self._audit(actor, user, "application.created", "application", application.application_id)
        if commit:
            await self.commit_conflict(["name"])
        else:
            try:
                await self.db.flush()
            except IntegrityError as error:
                await self.db.rollback()
                raise ConflictError(details={"fields": ["name"]}) from error
        return application

    async def list_applications(self, organization_id: UUID) -> list[Application]:
        result = await self.db.execute(
            select(Application)
            .where(Application.organization_id == organization_id)
            .order_by(Application.created_at.desc(), Application.application_id.desc())
        )
        return list(result.scalars())

    async def application(self, organization_id: UUID, application_id: UUID) -> Application:
        application = (
            await self.db.execute(
                select(Application).where(
                    Application.organization_id == organization_id,
                    Application.application_id == application_id,
                )
            )
        ).scalar_one_or_none()
        if application is None:
            raise NotFoundOrHiddenError()
        return application

    async def update_application(
        self,
        actor: Membership,
        user: User,
        application: Application,
        *,
        name: str | None,
        privacy_mode: PrivacyMode | None,
        safe_content_persistence: bool | None,
        security_retention_days: int | None,
    ) -> Application:
        self._require_editor(actor)
        privacy_change = any(
            value is not None
            for value in (privacy_mode, safe_content_persistence, security_retention_days)
        )
        if privacy_change and MembershipRole(actor.role) not in OPERATORS:
            raise AuthorizationError()
        if name is not None:
            application.name = self._name(name)
            application.name_key = application.name.casefold()
        if privacy_mode is not None:
            application.privacy_mode = privacy_mode.value
        if safe_content_persistence is not None:
            application.safe_content_persistence = safe_content_persistence
        if security_retention_days is not None:
            application.security_retention_days = security_retention_days
        self._audit(
            actor,
            user,
            "application.privacy_changed" if privacy_change else "application.updated",
            "application",
            application.application_id,
            {
                "privacy_mode": application.privacy_mode,
                "safe_content_persistence": application.safe_content_persistence,
                "security_retention_days": application.security_retention_days,
            }
            if privacy_change
            else {},
        )
        await self.commit_conflict(["name"])
        return application

    async def archive_application(
        self, actor: Membership, user: User, application: Application
    ) -> Application:
        self._require_editor(actor)
        if application.status != "archived":
            application.status = "archived"
            self._audit(
                actor,
                user,
                "application.archived",
                "application",
                application.application_id,
            )
            await self.db.commit()
        return application

    async def create_environment(
        self, actor: Membership, user: User, application: Application, environment_type: str
    ) -> Environment:
        self._require_editor(actor)
        if application.status != "active":
            raise ConflictError(details={"reason": "application_archived"})
        if environment_type not in ENVIRONMENT_TYPES:
            raise ConflictError(details={"fields": ["type"]})
        environment = Environment(
            environment_id=new_uuid7(),
            organization_id=application.organization_id,
            application_id=application.application_id,
            type=environment_type,
        )
        self.db.add(environment)
        self._audit(
            actor,
            user,
            "environment.created",
            "environment",
            environment.environment_id,
            {"type": environment.type},
        )
        await self.commit_conflict(["type"])
        return environment

    async def list_environments(
        self, organization_id: UUID, application_id: UUID
    ) -> list[Environment]:
        result = await self.db.execute(
            select(Environment)
            .where(
                Environment.organization_id == organization_id,
                Environment.application_id == application_id,
            )
            .order_by(Environment.type)
        )
        return list(result.scalars())

    async def environment(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID
    ) -> Environment:
        environment = (
            await self.db.execute(
                select(Environment).where(
                    Environment.organization_id == organization_id,
                    Environment.application_id == application_id,
                    Environment.environment_id == environment_id,
                )
            )
        ).scalar_one_or_none()
        if environment is None:
            raise NotFoundOrHiddenError()
        return environment

    async def update_environment(
        self, actor: Membership, user: User, environment: Environment, status: str
    ) -> Environment:
        self._require_editor(actor)
        environment.status = status
        self._audit(
            actor,
            user,
            "environment.changed",
            "environment",
            environment.environment_id,
            {"status": status},
        )
        await self.db.commit()
        return environment

    async def issue_key(
        self,
        actor: Membership,
        user: User,
        application: Application,
        environment: Environment,
        label: str,
        expires_at: datetime | None,
        *,
        audit_action: str = "application_key.created",
    ) -> tuple[ApplicationApiKey, str]:
        self._require_editor(actor)
        if application.status != "active" or environment.status != "active":
            raise ConflictError(details={"reason": "scope_inactive"})
        now = utc_now()
        if expires_at is not None:
            expiry = as_utc(expires_at)
            if expiry <= now or expiry > now + timedelta(days=self.maximum_key_expiry_days):
                raise ConflictError(details={"fields": ["expires_at"]})
            expires_at = expiry
        issued = self.key_crypto.issue(environment.type)
        row = ApplicationApiKey(
            key_id=new_uuid7(),
            organization_id=application.organization_id,
            application_id=application.application_id,
            environment_id=environment.environment_id,
            created_by_user_id=user.user_id,
            label=label.strip(),
            lookup=issued.lookup,
            prefix=issued.prefix,
            verifier=issued.verifier,
            verifier_key_id=self.key_crypto.key_id,
            expires_at=expires_at,
        )
        self.db.add(row)
        self._audit(
            actor,
            user,
            audit_action,
            "application_api_key",
            row.key_id,
            {"prefix": row.prefix, "environment_id": str(environment.environment_id)},
        )
        await self.db.commit()
        return row, issued.public

    async def list_keys(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID
    ) -> list[ApplicationApiKey]:
        result = await self.db.execute(
            select(ApplicationApiKey)
            .where(
                ApplicationApiKey.organization_id == organization_id,
                ApplicationApiKey.application_id == application_id,
                ApplicationApiKey.environment_id == environment_id,
            )
            .order_by(ApplicationApiKey.created_at.desc(), ApplicationApiKey.key_id.desc())
        )
        return list(result.scalars())

    async def key(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID, key_id: UUID
    ) -> ApplicationApiKey:
        key = (
            await self.db.execute(
                select(ApplicationApiKey).where(
                    ApplicationApiKey.organization_id == organization_id,
                    ApplicationApiKey.application_id == application_id,
                    ApplicationApiKey.environment_id == environment_id,
                    ApplicationApiKey.key_id == key_id,
                )
            )
        ).scalar_one_or_none()
        if key is None:
            raise NotFoundOrHiddenError()
        return key

    async def revoke_key(
        self, actor: Membership, user: User, key: ApplicationApiKey
    ) -> ApplicationApiKey:
        self._require_editor(actor)
        if key.revoked_at is None:
            key.revoked_at = utc_now()
            self._audit(
                actor,
                user,
                "application_key.revoked",
                "application_api_key",
                key.key_id,
                {"prefix": key.prefix},
            )
            await self.db.commit()
        return key

    async def rotate_key(
        self,
        actor: Membership,
        user: User,
        application: Application,
        environment: Environment,
        key: ApplicationApiKey,
        expires_at: datetime | None,
    ) -> tuple[ApplicationApiKey, str]:
        self._require_editor(actor)
        if key.revoked_at is not None:
            raise ConflictError(details={"reason": "key_revoked"})
        key.revoked_at = utc_now()
        retained_expiry = key.expires_at
        if retained_expiry is not None and as_utc(retained_expiry) <= utc_now():
            retained_expiry = None
        return await self.issue_key(
            actor,
            user,
            application,
            environment,
            key.label,
            expires_at if expires_at is not None else retained_expiry,
            audit_action="application_key.rotated",
        )

    @staticmethod
    def _name(name: str) -> str:
        return " ".join(name.strip().split())

    @staticmethod
    def _require_editor(actor: Membership) -> None:
        if MembershipRole(actor.role) not in APP_EDITORS:
            raise AuthorizationError()

    async def commit_conflict(self, fields: list[str]) -> None:
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": fields}) from error

    def _audit(
        self,
        actor: Membership,
        user: User,
        action: str,
        resource_type: str,
        resource_id: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=user.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata=metadata or {},
            )
        )
