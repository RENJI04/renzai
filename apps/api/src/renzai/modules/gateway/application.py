"""Gateway orchestration across input security, provider I/O, and output security."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import ConfigurationError, ValidationError
from renzai.core.ids import new_uuid7
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.gateway.domain import inspection_text, redact_messages
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.providers.application import ProviderService
from renzai.modules.providers.domain import (
    ProviderChatRequest,
    ProviderCompletion,
    ProviderConfigurationFailure,
    ProviderFailure,
    ProviderRuntimeConfig,
    ProviderTimeout,
)
from renzai.modules.security.application import AnalysisScope, AnalysisService
from renzai.modules.security.domain.normalization import NormalizationLimitError
from renzai.modules.security.domain.types import Direction, InspectionFailure


class GatewayPolicyBlock(RuntimeError):
    def __init__(self, phase: str, analysis_id: str) -> None:
        self.phase = phase
        self.analysis_id = analysis_id


class GatewayReviewRequired(RuntimeError):
    def __init__(self, phase: str, analysis_id: str) -> None:
        self.phase = phase
        self.analysis_id = analysis_id


class GatewayProviderTimeout(RuntimeError):
    pass


class GatewayProviderError(RuntimeError):
    pass


class GatewayInspectionFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GatewayContext:
    organization_id: UUID
    application_id: UUID
    environment_id: UUID
    correlation_id: str
    application: Application
    environment: Environment


class GatewayService:
    def __init__(
        self,
        db: AsyncSession,
        provider_service: ProviderService,
    ) -> None:
        self.db = db
        self.provider_service = provider_service

    async def complete(
        self,
        context: GatewayContext,
        request: ProviderChatRequest,
    ) -> tuple[ProviderCompletion, str | None, dict[str, object], dict[str, int]]:
        scope = AnalysisScope(
            context.organization_id,
            context.application_id,
            context.environment_id,
            context.environment.type,
            context.correlation_id,
        )
        input_started = perf_counter_ns()
        try:
            input_analysis = await AnalysisService(self.db).analyze(
                scope,
                context.application,
                inspection_text(request.messages),
                Direction.INPUT,
                "gateway",
            )
        except (InspectionFailure, NormalizationLimitError, SQLAlchemyError) as error:
            await self.db.rollback()
            raise GatewayInspectionFailure() from error
        input_ms = (perf_counter_ns() - input_started) // 1_000_000
        input_action = str(input_analysis["action"])
        input_analysis_id = str(input_analysis["analysis_id"])
        if input_action == "block":
            raise GatewayPolicyBlock("input", input_analysis_id)
        if input_action == "require_review":
            raise GatewayReviewRequired("input", input_analysis_id)
        messages = request.messages
        if input_action == "redact":
            decision = input_analysis.get("policy_decision")
            targets = decision.get("redaction_targets", []) if isinstance(decision, dict) else []
            try:
                messages = redact_messages(messages, frozenset(str(item) for item in targets))
            except InspectionFailure as error:
                raise GatewayInspectionFailure() from error

        provider_row = await self.provider_service.select_for_gateway(
            context.organization_id,
            context.application_id,
            context.environment_id,
            request.model,
        )
        if request.max_tokens is not None and request.max_tokens > provider_row.max_tokens:
            raise ValidationError(details={"fields": ["max_tokens"]})
        if request.seed is not None and not provider_row.supports_seed:
            raise ValidationError(details={"fields": ["seed"]})
        runtime = self.provider_service.runtime(provider_row)
        await self.db.commit()
        forwarded = ProviderChatRequest(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stop=request.stop,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty,
            seed=request.seed,
        )
        provider_started = perf_counter_ns()
        try:
            completion = await self.provider_service.chat_provider.complete(forwarded, runtime)
        except ProviderTimeout as error:
            provider_ms = (perf_counter_ns() - provider_started) // 1_000_000
            await self._record_call(
                runtime,
                UUID(input_analysis_id),
                None,
                context.correlation_id,
                provider_ms,
                None,
                "provider_timeout",
            )
            raise GatewayProviderTimeout() from error
        except ProviderConfigurationFailure as error:
            provider_ms = (perf_counter_ns() - provider_started) // 1_000_000
            await self._record_call(
                runtime,
                UUID(input_analysis_id),
                None,
                context.correlation_id,
                provider_ms,
                None,
                "configuration_error",
            )
            raise ConfigurationError() from error
        except ProviderFailure as error:
            provider_ms = (perf_counter_ns() - provider_started) // 1_000_000
            await self._record_call(
                runtime,
                UUID(input_analysis_id),
                None,
                context.correlation_id,
                provider_ms,
                None,
                "provider_error",
            )
            raise GatewayProviderError() from error
        provider_ms = (perf_counter_ns() - provider_started) // 1_000_000

        output_started = perf_counter_ns()
        try:
            output_analysis = await AnalysisService(self.db).analyze(
                scope,
                context.application,
                completion.content,
                Direction.OUTPUT,
                "gateway",
            )
        except (InspectionFailure, NormalizationLimitError, SQLAlchemyError) as error:
            await self.db.rollback()
            failed_analysis_id = (
                UUID(error.analysis_id)
                if isinstance(error, InspectionFailure) and error.analysis_id is not None
                else None
            )
            await self._record_call(
                runtime,
                UUID(input_analysis_id),
                failed_analysis_id,
                context.correlation_id,
                provider_ms,
                2,
                "output_inspection_failure",
            )
            raise GatewayInspectionFailure() from error
        output_ms = (perf_counter_ns() - output_started) // 1_000_000
        output_action = str(output_analysis["action"])
        output_analysis_id = str(output_analysis["analysis_id"])
        redacted: str | None = None
        if output_action == "redact":
            value = output_analysis.get("redacted_content")
            if not isinstance(value, str) or not value:
                await self._record_call(
                    runtime,
                    UUID(input_analysis_id),
                    UUID(output_analysis_id),
                    context.correlation_id,
                    provider_ms,
                    2,
                    "output_inspection_failure",
                )
                raise GatewayInspectionFailure()
            redacted = value
        outcome = "completed"
        if output_action == "block":
            outcome = "output_block"
        elif output_action == "require_review":
            outcome = "output_review"
        await self._record_call(
            runtime,
            UUID(input_analysis_id),
            UUID(output_analysis_id),
            context.correlation_id,
            provider_ms,
            2,
            outcome,
        )
        if output_action == "block":
            raise GatewayPolicyBlock("output", output_analysis_id)
        if output_action == "require_review":
            raise GatewayReviewRequired("output", output_analysis_id)
        return (
            completion,
            redacted,
            {
                "input": input_analysis,
                "output": output_analysis,
            },
            {
                "input_security_ms": input_ms,
                "provider_ms": provider_ms,
                "output_security_ms": output_ms,
                "total_ms": input_ms + provider_ms + output_ms,
            },
        )

    async def _record_call(
        self,
        provider: ProviderRuntimeConfig,
        input_analysis_id: UUID,
        output_analysis_id: UUID | None,
        correlation_id: str,
        latency_ms: int,
        status_class: int | None,
        outcome: str,
    ) -> None:
        self.db.add(
            GatewayProviderCall(
                gateway_call_id=new_uuid7(),
                organization_id=provider.organization_id,
                application_id=provider.application_id,
                environment_id=provider.environment_id,
                provider_id=provider.provider_id,
                input_analysis_id=input_analysis_id,
                output_analysis_id=output_analysis_id,
                correlation_id=correlation_id,
                configured_model=provider.model,
                provider_latency_ms=latency_ms,
                status_class=status_class,
                outcome=outcome,
            )
        )
        try:
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            raise GatewayInspectionFailure() from error
