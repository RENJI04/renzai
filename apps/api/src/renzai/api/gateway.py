"""Limited, non-streaming OpenAI-compatible Gateway route."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    ApplicationContext,
    application_context,
    get_application_key_crypto,
    get_db,
)
from renzai.core.errors import (
    InspectionFailureError,
    PolicyBlockError,
    ProviderError,
    ProviderTimeoutError,
    ReviewRequiredError,
    ValidationError,
)
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.modules.gateway.application import (
    GatewayContext,
    GatewayInspectionFailure,
    GatewayPolicyBlock,
    GatewayProviderError,
    GatewayProviderTimeout,
    GatewayReviewRequired,
    GatewayService,
)
from renzai.modules.providers.application import ProviderService
from renzai.modules.providers.domain import ChatMessage, ProviderChatRequest

router = APIRouter(tags=["gateway"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GatewayMessage(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=128 * 1024)

    @field_validator("content")
    @classmethod
    def content_is_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message content cannot be blank")
        return value


class GatewayRequest(StrictModel):
    model: str = Field(min_length=1, max_length=160)
    messages: list[GatewayMessage] = Field(min_length=1, max_length=32)
    stream: Literal[False] = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    stop: str | list[str] | None = None
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    seed: int | None = Field(default=None, ge=-(2**31), le=2**31 - 1)

    @field_validator("stop")
    @classmethod
    def validate_stop(cls, value: str | list[str] | None) -> str | list[str] | None:
        if value is None:
            return value
        values = [value] if isinstance(value, str) else value
        if not 1 <= len(values) <= 4 or any(not item or len(item) > 1024 for item in values):
            raise ValueError("stop must contain one to four bounded strings")
        return value


@router.post("/v1/chat/completions")
async def chat_completions(
    body: GatewayRequest,
    request: Request,
    context: Annotated[ApplicationContext, Depends(application_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> JSONResponse:
    settings = request.app.state.settings
    encoded = json.dumps(body.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")
    if len(encoded) > settings.gateway.max_body_bytes:
        raise ValidationError(details={"fields": ["body"]})
    messages = tuple(ChatMessage(item.role, item.content) for item in body.messages)
    combined_bytes = sum(len(item.content.encode("utf-8")) for item in messages)
    if (
        len(messages) > settings.gateway.max_message_count
        or combined_bytes > settings.gateway.max_combined_message_bytes
    ):
        raise ValidationError(details={"fields": ["messages"]})
    bucket = key_crypto.rate_limit_identifier(str(context.key_id))
    await request.app.state.dependencies.gateway_rate_limiter.check(bucket)
    dependencies = request.app.state.dependencies
    provider_service = ProviderService(
        db,
        dependencies.provider_credential_key_ring,
        dependencies.outbound_target_guard,
        dependencies.chat_provider,
    )
    service = GatewayService(db, provider_service)
    stop = tuple(body.stop) if isinstance(body.stop, list) else body.stop
    try:
        completion, redacted, analyses, _timing = await service.complete(
            GatewayContext(
                organization_id=context.organization_id,
                application_id=context.application_id,
                environment_id=context.environment_id,
                correlation_id=context.correlation_id,
                application=context.application,
                environment=context.environment,
            ),
            ProviderChatRequest(
                model=body.model,
                messages=messages,
                temperature=body.temperature,
                top_p=body.top_p,
                max_tokens=body.max_tokens,
                stop=stop,
                presence_penalty=body.presence_penalty,
                frequency_penalty=body.frequency_penalty,
                seed=body.seed,
            ),
        )
    except GatewayPolicyBlock as error:
        raise PolicyBlockError(details={"phase": error.phase}) from error
    except GatewayReviewRequired as error:
        raise ReviewRequiredError(details={"phase": error.phase}) from error
    except GatewayProviderTimeout as error:
        raise ProviderTimeoutError() from error
    except GatewayProviderError as error:
        raise ProviderError() from error
    except GatewayInspectionFailure as error:
        raise InspectionFailureError() from error
    input_analysis = analyses["input"]
    output_analysis = analyses["output"]
    assert isinstance(input_analysis, dict) and isinstance(output_analysis, dict)
    response = JSONResponse(completion.response(redacted))
    response.headers["X-Renzai-Request-ID"] = context.correlation_id
    response.headers["X-Renzai-Input-Analysis-ID"] = str(input_analysis["analysis_id"])
    response.headers["X-Renzai-Output-Analysis-ID"] = str(output_analysis["analysis_id"])
    response.headers["X-Renzai-Input-Action"] = str(input_analysis["action"])
    response.headers["X-Renzai-Output-Action"] = str(output_analysis["action"])
    return response
