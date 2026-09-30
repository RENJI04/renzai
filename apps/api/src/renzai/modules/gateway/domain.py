"""Pure Gateway message representation and per-message redaction helpers."""

from __future__ import annotations

from renzai.modules.providers.domain import ChatMessage
from renzai.modules.security.domain.engine import SecurityEngine, render_redacted
from renzai.modules.security.domain.types import Direction, InspectionFailure

MESSAGE_REPRESENTATION_VERSION = "gateway-messages-v1"


def inspection_text(messages: tuple[ChatMessage, ...]) -> str:
    return "\n\n".join(f"[{message.role}]\n{message.content}" for message in messages)


def redact_messages(
    messages: tuple[ChatMessage, ...], categories: frozenset[str]
) -> tuple[ChatMessage, ...]:
    engine = SecurityEngine()
    result: list[ChatMessage] = []
    applied_any = False
    for message in messages:
        computation = engine.analyze(message.content, Direction.INPUT)
        redacted, applied = render_redacted(computation, categories)
        applied_any = applied_any or applied
        result.append(ChatMessage(message.role, redacted if applied else message.content))
    if not applied_any:
        raise InspectionFailure("input redact policy has no validated redaction target")
    return tuple(result)
