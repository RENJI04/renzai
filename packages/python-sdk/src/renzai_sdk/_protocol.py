"""Response validation and safe error normalization."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal, NoReturn, TypeVar, cast

from renzai_sdk.errors import ERROR_TYPES, RenzaiError, RenzaiProtocolError
from renzai_sdk.models import (
    Action,
    AIIntelligenceResult,
    AIStatus,
    AITaskType,
    AnalyticsDashboard,
    AnalyzeResult,
    Category,
    ChatCompletion,
    Direction,
    DisclosureMode,
    Finding,
    Incident,
    IncidentPage,
    IncidentSeverity,
    IncidentStatus,
    JsonObject,
    PolicyDecision,
    Severity,
)

EnumT = TypeVar("EnumT", bound=StrEnum)


def request_id_from_headers(headers: Mapping[str, str]) -> str | None:
    return headers.get("x-renzai-request-id") or headers.get("x-request-id")


def raise_error(payload: object, status_code: int, headers: Mapping[str, str]) -> NoReturn:
    request_id = request_id_from_headers(headers)
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), dict):
        raise RenzaiProtocolError(
            "Renzai returned a malformed error response.",
            code="protocol_error",
            request_id=request_id,
            status_code=status_code,
        )
    envelope = cast(dict[str, object], payload["error"])
    code = envelope.get("code")
    message = envelope.get("message")
    body_request_id = envelope.get("request_id")
    details = envelope.get("details")
    if not isinstance(code, str) or not isinstance(message, str):
        raise RenzaiProtocolError(
            "Renzai returned a malformed error response.",
            code="protocol_error",
            request_id=request_id,
            status_code=status_code,
        )
    if isinstance(body_request_id, str):
        request_id = body_request_id
    safe_details = details if isinstance(details, dict) else None
    error_type = ERROR_TYPES.get(code, RenzaiError)
    raise error_type(
        message,
        code=code,
        request_id=request_id,
        details=cast(dict[str, Any] | None, safe_details),
        status_code=status_code,
    )


def as_object(value: object, label: str = "response") -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RenzaiProtocolError(f"Renzai returned a malformed {label}.", code="protocol_error")
    return cast(JsonObject, value)


def _string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise RenzaiProtocolError(f"Renzai response is missing {key}.", code="protocol_error")
    return value


def _integer(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RenzaiProtocolError(f"Renzai response is missing {key}.", code="protocol_error")
    return value


def _boolean(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise RenzaiProtocolError(f"Renzai response is missing {key}.", code="protocol_error")
    return value


def _enum(enum_type: type[EnumT], data: Mapping[str, Any], key: str) -> EnumT:
    value = _string(data, key)
    try:
        return enum_type(value)
    except ValueError as error:
        raise RenzaiProtocolError(
            f"Renzai response contains an invalid {key}.", code="protocol_error"
        ) from error


def parse_analyze(payload: object, request_id: str | None) -> AnalyzeResult:
    data = as_object(payload, "Analyze response")
    raw_findings = data.get("findings")
    raw_policy = data.get("policy_decision")
    if not isinstance(raw_findings, list) or not isinstance(raw_policy, dict):
        raise RenzaiProtocolError(
            "Renzai returned a malformed Analyze response.", code="protocol_error"
        )
    findings: list[Finding] = []
    for item in raw_findings:
        row = as_object(item, "finding")
        evidence = as_object(row.get("evidence"), "finding evidence")
        metadata_value = row.get("metadata")
        metadata = (
            {str(key): str(value) for key, value in metadata_value.items()}
            if isinstance(metadata_value, dict)
            else {}
        )
        findings.append(
            Finding(
                finding_id=_string(row, "finding_id"),
                detector_id=_string(row, "detector_id"),
                detector_version=_string(row, "detector_version"),
                ruleset_version=_string(row, "ruleset_version"),
                category=_enum(Category, row, "category"),
                direction=_enum(Direction, row, "direction"),
                severity=_enum(Severity, row, "severity"),
                confidence=_integer(row, "confidence"),
                safe_explanation=_string(row, "safe_explanation"),
                evidence=evidence,
                metadata=metadata,
            )
        )
    policy = cast(JsonObject, raw_policy)
    redaction_targets = policy.get("redaction_targets")
    evaluated = policy.get("evaluated_policy_versions")
    winners = policy.get("scope_winners")
    policy_match = policy.get("policy_match")
    decision = PolicyDecision(
        policy_decision_id=_string(policy, "policy_decision_id"),
        rationale_code=_string(policy, "rationale_code"),
        redaction_targets=tuple(str(item) for item in redaction_targets)
        if isinstance(redaction_targets, list)
        else (),
        policy_match=as_object(policy_match, "policy match") if policy_match is not None else None,
        evaluated_policy_versions=tuple(as_object(item) for item in evaluated)
        if isinstance(evaluated, list)
        else (),
        scope_winners=tuple(as_object(item) for item in winners)
        if isinstance(winners, list)
        else (),
    )
    confidence = _integer(data, "confidence")
    if not 0 <= confidence <= 100:
        raise RenzaiProtocolError("Renzai returned an invalid confidence.", code="protocol_error")
    risk_score = _integer(data, "risk_score")
    if not 0 <= risk_score <= 100:
        raise RenzaiProtocolError("Renzai returned an invalid risk score.", code="protocol_error")
    contributions = data.get("risk_contributions")
    return AnalyzeResult(
        analysis_id=_string(data, "analysis_id"),
        event_id=_string(data, "event_id"),
        timestamp=_string(data, "timestamp"),
        direction=_enum(Direction, data, "direction"),
        source=_string(data, "source"),
        safe=_boolean(data, "safe"),
        no_detected_threat=_boolean(data, "no_detected_threat"),
        action=_enum(Action, data, "action"),
        risk_score=risk_score,
        severity=_enum(Severity, data, "severity"),
        confidence=confidence,
        normalization_version=_string(data, "normalization_version"),
        detector_ruleset_version=_string(data, "detector_ruleset_version"),
        findings=tuple(findings),
        risk_profile=as_object(data.get("risk_profile"), "risk profile"),
        risk_contributions=tuple(as_object(item) for item in contributions)
        if isinstance(contributions, list)
        else (),
        risk_explanation=as_object(data.get("risk_explanation"), "risk explanation"),
        policy_decision=decision,
        timing=as_object(data.get("timing"), "timing"),
        correlation_id=_string(data, "correlation_id"),
        redacted_content=(
            cast(str, data["redacted_content"])
            if isinstance(data.get("redacted_content"), str)
            else None
        ),
        request_id=request_id,
    )


def parse_chat(payload: object, headers: Mapping[str, str]) -> ChatCompletion:
    data = as_object(payload, "Gateway response")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise RenzaiProtocolError(
            "Renzai returned a malformed Gateway response.", code="protocol_error"
        )
    choice = as_object(choices[0], "Gateway choice")
    message = as_object(choice.get("message"), "Gateway message")
    content = message.get("content")
    if message.get("role") != "assistant" or not isinstance(content, str):
        raise RenzaiProtocolError(
            "Renzai returned a malformed Gateway message.", code="protocol_error"
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason not in {"stop", "length"}:
        raise RenzaiProtocolError(
            "Renzai returned an invalid finish reason.", code="protocol_error"
        )
    usage_value = data.get("usage")
    usage = None
    if usage_value is not None:
        usage_object = as_object(usage_value, "Gateway usage")
        if any(
            isinstance(value, bool) or not isinstance(value, int) for value in usage_object.values()
        ):
            raise RenzaiProtocolError("Renzai returned invalid usage data.", code="protocol_error")
        usage = cast(dict[str, int], usage_object)
    input_action = headers.get("x-renzai-input-action")
    output_action = headers.get("x-renzai-output-action")
    return ChatCompletion(
        id=_string(data, "id"),
        created=_integer(data, "created"),
        model=_string(data, "model"),
        content=content,
        finish_reason=cast(Literal["stop", "length"], finish_reason),
        usage=usage,
        request_id=request_id_from_headers(headers),
        input_analysis_id=headers.get("x-renzai-input-analysis-id"),
        output_analysis_id=headers.get("x-renzai-output-analysis-id"),
        input_action=_enum(Action, {"action": input_action}, "action") if input_action else None,
        output_action=_enum(Action, {"action": output_action}, "action") if output_action else None,
    )


def parse_incident(payload: object) -> Incident:
    data = as_object(payload, "incident")
    action = data.get("action")
    return Incident(
        incident_id=_string(data, "incident_id"),
        organization_id=_string(data, "organization_id"),
        status=_enum(IncidentStatus, data, "status"),
        severity=_enum(IncidentSeverity, data, "severity"),
        source=cast(Literal["manual", "gateway", "analyze", "playground"], _string(data, "source")),
        title=_string(data, "title"),
        safe_summary=_string(data, "safe_summary"),
        version=_integer(data, "version"),
        created_at=_string(data, "created_at"),
        updated_at=_string(data, "updated_at"),
        application_id=cast(str | None, data.get("application_id")),
        environment_id=cast(str | None, data.get("environment_id")),
        assignee_user_id=cast(str | None, data.get("assignee_user_id")),
        action=_enum(Action, {"action": action}, "action") if isinstance(action, str) else None,
        risk_score=cast(int | None, data.get("risk_score")),
        category=cast(str | None, data.get("category")),
        resolved_at=cast(str | None, data.get("resolved_at")),
        details=data,
    )


def parse_incident_page(payload: object, request_id: str | None) -> IncidentPage:
    data = as_object(payload, "incident page")
    items = data.get("items")
    cursor = data.get("next_cursor")
    if not isinstance(items, list) or (cursor is not None and not isinstance(cursor, str)):
        raise RenzaiProtocolError(
            "Renzai returned a malformed incident page.", code="protocol_error"
        )
    return IncidentPage(
        items=tuple(parse_incident(item) for item in items),
        next_cursor=cursor,
        limit=_integer(data, "limit"),
        request_id=request_id,
    )


def parse_analytics(payload: object, request_id: str | None) -> AnalyticsDashboard:
    data = as_object(payload, "analytics response")

    def objects(key: str) -> tuple[JsonObject, ...]:
        value = data.get(key)
        if not isinstance(value, list):
            raise RenzaiProtocolError(f"Renzai response is missing {key}.", code="protocol_error")
        return tuple(as_object(item, key) for item in value)

    return AnalyticsDashboard(
        filters=as_object(data.get("filters"), "analytics filters"),
        summary=as_object(data.get("summary"), "analytics summary"),
        activity=objects("activity"),
        risk_distribution=objects("risk_distribution"),
        threat_categories=objects("threat_categories"),
        top_detectors=objects("top_detectors"),
        policy_actions=objects("policy_actions"),
        applications=objects("applications"),
        environments=objects("environments"),
        providers=objects("providers"),
        incidents=as_object(data.get("incidents"), "incident analytics"),
        recent_incidents=objects("recent_incidents"),
        query_duration_ms=_integer(data, "query_duration_ms"),
        request_id=request_id,
    )


def parse_ai(payload: object, response_request_id: str | None) -> AIIntelligenceResult:
    data = as_object(payload, "AI intelligence response")
    content_value = data.get("content")
    usage_value = data.get("usage")
    return AIIntelligenceResult(
        request_id=_string(data, "request_id"),
        incident_id=_string(data, "incident_id"),
        task_type=_enum(AITaskType, data, "task_type"),
        status=_enum(AIStatus, data, "status"),
        ai_generated=_boolean(data, "ai_generated"),
        context_mode=_enum(DisclosureMode, data, "context_mode"),
        incident_version=_integer(data, "incident_version"),
        provider_id=_string(data, "provider_id"),
        provider_name=_string(data, "provider_name"),
        model=_string(data, "model"),
        prompt_template_version=cast(str | None, data.get("prompt_template_version")),
        input_context_version=_string(data, "input_context_version"),
        output_schema_version=_string(data, "output_schema_version"),
        content=as_object(content_value, "AI content") if content_value is not None else None,
        usage=cast(
            dict[str, int | None] | None, usage_value if isinstance(usage_value, dict) else None
        ),
        error_code=cast(str | None, data.get("error_code")),
        created_at=_string(data, "created_at"),
        completed_at=cast(str | None, data.get("completed_at")),
        response_request_id=response_request_id,
    )
