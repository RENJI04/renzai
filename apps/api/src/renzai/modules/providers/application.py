"""Provider configuration use cases with tenant authorization and safe auditing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import (
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    NotFoundOrHiddenError,
    ValidationError,
)
from renzai.core.ids import new_uuid7
from renzai.core.request_context import get_request_id
from renzai.core.time import utc_now
from renzai.infrastructure.crypto.provider_credentials import (
    ProviderCredentialKeyRing,
    provider_credential_context,
)
from renzai.infrastructure.http.outbound import OutboundTargetGuard, ResolvedTarget
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AuditEvent
from renzai.modules.environments.models import Environment
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.providers.domain import (
    ChatProvider,
    ProviderConfigurationFailure,
    ProviderFailure,
    ProviderRuntimeConfig,
)
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.users.models import User

PROVIDER_EDITORS = {MembershipRole.OWNER, MembershipRole.ADMIN}
PROVIDER_KINDS = {"openai_compatible_remote", "openai_compatible_local"}


class ProviderService:
    def __init__(
        self,
        db: AsyncSession,
        key_ring: ProviderCredentialKeyRing,
        target_guard: OutboundTargetGuard,
        chat_provider: ChatProvider,
    ) -> None:
        self.db = db
        self.key_ring = key_ring
        self.target_guard = target_guard
        self.chat_provider = chat_provider

    async def create(
        self,
        actor: Membership,
        user: User,
        *,
        application_id: UUID,
        environment_id: UUID,
        kind: str,
        name: str,
        base_url: str,
        model: str,
        credential: str | None,
        supports_seed: bool,
        max_tokens: int,
        connect_timeout_seconds: int,
        chat_timeout_seconds: int,
        health_timeout_seconds: int,
        response_max_bytes: int,
    ) -> ProviderConfiguration:
        self.require_editor(actor)
        await self._require_scope(actor.organization_id, application_id, environment_id)
        if kind not in PROVIDER_KINDS:
            raise ConflictError(details={"fields": ["kind"]})
        if kind == "openai_compatible_remote" and not credential:
            raise ValidationError(details={"fields": ["credential"]})
        self._validate_credential(credential)
        target = await self._validated_target(base_url, kind)
        provider_id = new_uuid7()
        encrypted = (
            self.key_ring.encrypt(
                credential,
                provider_credential_context(
                    provider_id, actor.organization_id, application_id, environment_id
                ),
            )
            if credential
            else None
        )
        clean_name = self._clean(name)
        row = ProviderConfiguration(
            provider_id=provider_id,
            organization_id=actor.organization_id,
            application_id=application_id,
            environment_id=environment_id,
            kind=kind,
            name=clean_name,
            name_key=clean_name.casefold(),
            base_url=target.url,
            model=self._clean(model),
            credential_ciphertext=encrypted.ciphertext if encrypted else None,
            credential_key_id=encrypted.key_id if encrypted else None,
            supports_seed=supports_seed,
            max_tokens=max_tokens,
            connect_timeout_seconds=connect_timeout_seconds,
            chat_timeout_seconds=chat_timeout_seconds,
            health_timeout_seconds=health_timeout_seconds,
            response_max_bytes=response_max_bytes,
            validation_policy_version="1.0.0",
        )
        self.db.add(row)
        self._audit(actor, user, "provider.created", row)
        await self._commit_conflict()
        return row

    async def list(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID
    ) -> list[ProviderConfiguration]:
        await self._require_scope(organization_id, application_id, environment_id)
        rows = await self.db.execute(
            select(ProviderConfiguration)
            .where(
                ProviderConfiguration.organization_id == organization_id,
                ProviderConfiguration.application_id == application_id,
                ProviderConfiguration.environment_id == environment_id,
            )
            .order_by(
                ProviderConfiguration.created_at.desc(), ProviderConfiguration.provider_id.desc()
            )
        )
        return list(rows.scalars())

    async def get(
        self,
        organization_id: UUID,
        application_id: UUID,
        environment_id: UUID,
        provider_id: UUID,
    ) -> ProviderConfiguration:
        row = (
            await self.db.execute(
                select(ProviderConfiguration).where(
                    ProviderConfiguration.organization_id == organization_id,
                    ProviderConfiguration.application_id == application_id,
                    ProviderConfiguration.environment_id == environment_id,
                    ProviderConfiguration.provider_id == provider_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundOrHiddenError()
        return row

    async def update(
        self,
        actor: Membership,
        user: User,
        row: ProviderConfiguration,
        *,
        kind: str | None,
        name: str | None,
        base_url: str | None,
        model: str | None,
        credential: str | None,
        supports_seed: bool | None,
        max_tokens: int | None,
        connect_timeout_seconds: int | None,
        chat_timeout_seconds: int | None,
        health_timeout_seconds: int | None,
        response_max_bytes: int | None,
    ) -> ProviderConfiguration:
        self.require_editor(actor)
        next_kind = kind or row.kind
        if next_kind not in PROVIDER_KINDS:
            raise ValidationError(details={"fields": ["kind"]})
        next_url = base_url or row.base_url
        target = await self._validated_target(next_url, next_kind)
        if next_kind == "openai_compatible_remote" and not (
            credential or row.credential_ciphertext
        ):
            raise ValidationError(details={"fields": ["credential"]})
        self._validate_credential(credential)
        row.kind = next_kind
        row.base_url = target.url
        if name is not None:
            row.name = self._clean(name)
            row.name_key = row.name.casefold()
        if model is not None:
            row.model = self._clean(model)
        if credential is not None:
            encrypted = self.key_ring.encrypt(
                credential,
                provider_credential_context(
                    row.provider_id,
                    row.organization_id,
                    row.application_id,
                    row.environment_id,
                ),
            )
            row.credential_ciphertext = encrypted.ciphertext
            row.credential_key_id = encrypted.key_id
        if supports_seed is not None:
            row.supports_seed = supports_seed
        if max_tokens is not None:
            row.max_tokens = max_tokens
        if connect_timeout_seconds is not None:
            row.connect_timeout_seconds = connect_timeout_seconds
        if chat_timeout_seconds is not None:
            row.chat_timeout_seconds = chat_timeout_seconds
        if health_timeout_seconds is not None:
            row.health_timeout_seconds = health_timeout_seconds
        if response_max_bytes is not None:
            row.response_max_bytes = response_max_bytes
        row.last_validation_status = "never"
        row.last_validated_at = None
        self._audit(
            actor,
            user,
            "provider.credential_replaced" if credential is not None else "provider.updated",
            row,
        )
        await self._commit_conflict()
        return row

    async def set_enabled(
        self,
        actor: Membership,
        user: User,
        row: ProviderConfiguration,
        *,
        enabled: bool,
    ) -> ProviderConfiguration:
        self.require_editor(actor)
        row.status = "active" if enabled else "disabled"
        self._audit(actor, user, "provider.enabled" if enabled else "provider.disabled", row)
        await self.db.commit()
        return row

    async def validate_configuration(
        self, actor: Membership, user: User, row: ProviderConfiguration
    ) -> ProviderConfiguration:
        self.require_editor(actor)
        runtime = self.runtime(row)
        await self.db.commit()
        try:
            await self.chat_provider.check_health(runtime)
            row.last_validation_status = "success"
        except ProviderFailure:
            row.last_validation_status = "failure"
        row.last_validated_at = utc_now()
        self._audit(
            actor,
            user,
            "provider.validated",
            row,
            {"result": row.last_validation_status},
        )
        await self.db.commit()
        return row

    async def select_for_gateway(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID, model: str
    ) -> ProviderConfiguration:
        rows = list(
            (
                await self.db.execute(
                    select(ProviderConfiguration).where(
                        ProviderConfiguration.organization_id == organization_id,
                        ProviderConfiguration.application_id == application_id,
                        ProviderConfiguration.environment_id == environment_id,
                        ProviderConfiguration.status == "active",
                    )
                )
            ).scalars()
        )
        if not rows:
            raise ConfigurationError(details={"reason": "provider_selection"})
        matches = [row for row in rows if row.model == model]
        if not matches:
            raise ValidationError(details={"fields": ["model"]})
        if len(matches) != 1:
            raise ConfigurationError(details={"reason": "provider_selection"})
        return matches[0]

    @staticmethod
    def runtime(row: ProviderConfiguration) -> ProviderRuntimeConfig:
        return ProviderRuntimeConfig(
            provider_id=row.provider_id,
            organization_id=row.organization_id,
            application_id=row.application_id,
            environment_id=row.environment_id,
            kind=row.kind,
            base_url=row.base_url,
            model=row.model,
            credential_ciphertext=row.credential_ciphertext,
            credential_key_id=row.credential_key_id,
            connect_timeout_seconds=row.connect_timeout_seconds,
            chat_timeout_seconds=row.chat_timeout_seconds,
            health_timeout_seconds=row.health_timeout_seconds,
            response_max_bytes=row.response_max_bytes,
        )

    @staticmethod
    def require_editor(actor: Membership) -> None:
        if MembershipRole(actor.role) not in PROVIDER_EDITORS:
            raise AuthorizationError()

    async def _require_scope(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID
    ) -> None:
        scope = (
            await self.db.execute(
                select(Environment.environment_id)
                .join(Application, Application.application_id == Environment.application_id)
                .where(
                    Environment.organization_id == organization_id,
                    Environment.application_id == application_id,
                    Environment.environment_id == environment_id,
                    Application.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()
        if scope is None:
            raise NotFoundOrHiddenError()

    async def _commit_conflict(self) -> None:
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": ["name"]}) from error

    def _audit(
        self,
        actor: Membership,
        user: User,
        action: str,
        row: ProviderConfiguration,
        metadata: dict[str, object] | None = None,
    ) -> None:
        safe = {
            "application_id": str(row.application_id),
            "environment_id": str(row.environment_id),
            "kind": row.kind,
            "credential_present": row.credential_ciphertext is not None,
            **(metadata or {}),
        }
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=user.user_id,
                action=action,
                resource_type="provider_configuration",
                resource_id=str(row.provider_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata=safe,
            )
        )

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _validate_credential(value: str | None) -> None:
        if value is not None and any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise ValidationError(details={"fields": ["credential"]})

    async def _validated_target(self, url: str, kind: str) -> ResolvedTarget:
        try:
            return await self.target_guard.resolve(url, kind)
        except ProviderConfigurationFailure as error:
            raise ValidationError(details={"fields": ["base_url"]}) from error
