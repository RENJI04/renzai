"""Typed, forward-compatible models for implemented Renzai API v1 responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Protocol

JsonObject = dict[str, Any]


class Direction(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(StrEnum):
    PROMPT_INJECTION = "prompt_injection"
    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    JAILBREAK = "jailbreak"
    ROLE_MANIPULATION = "role_manipulation"
    ENCODED_OBFUSCATED = "encoded_obfuscated"
    SECRET_EXPOSURE = "secret_exposure"  # noqa: S105 - detector category, not a credential
    PII_EXPOSURE = "pii_exposure"
    SUSPICIOUS_URL = "suspicious_url"
    TOOL_MANIPULATION_INDICATOR = "tool_manipulation_indicator"
    DATA_EXFILTRATION_INDICATOR = "data_exfiltration_indicator"


class Action(StrEnum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    REDACT = "redact"
    REQUIRE_REVIEW = "require_review"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    FALSE_POSITIVE = "false_positive"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AITaskType(StrEnum):
    INCIDENT_SUMMARY = "incident_summary"
    ATTACK_EXPLANATION = "attack_explanation"
    MITIGATION_SUGGESTION = "mitigation_suggestion"
    POLICY_SUGGESTION = "policy_suggestion"


class DisclosureMode(StrEnum):
    METADATA_ONLY = "metadata_only"
    REDACTED = "redacted"
    FULL = "full"


class AIStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.25
    maximum_backoff_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not 0 <= self.initial_backoff_seconds <= 10:
            raise ValueError("initial_backoff_seconds must be between 0 and 10")
        if not 0 <= self.maximum_backoff_seconds <= 30:
            raise ValueError("maximum_backoff_seconds must be between 0 and 30")


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    detector_id: str
    detector_version: str
    ruleset_version: str
    category: Category
    direction: Direction
    severity: Severity
    confidence: int
    safe_explanation: str
    evidence: JsonObject
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    policy_decision_id: str
    rationale_code: str
    redaction_targets: tuple[str, ...]
    policy_match: JsonObject | None
    evaluated_policy_versions: tuple[JsonObject, ...]
    scope_winners: tuple[JsonObject, ...]


class RiskResult(Protocol):
    """Structural view of the exact flattened risk fields on an Analyze result."""

    @property
    def risk_score(self) -> int: ...

    @property
    def severity(self) -> Severity: ...

    @property
    def confidence(self) -> int: ...

    @property
    def risk_profile(self) -> JsonObject: ...

    @property
    def risk_contributions(self) -> tuple[JsonObject, ...]: ...

    @property
    def risk_explanation(self) -> JsonObject: ...


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    analysis_id: str
    event_id: str
    timestamp: str
    direction: Direction
    source: str
    safe: bool
    no_detected_threat: bool
    action: Action
    risk_score: int
    severity: Severity
    confidence: int
    normalization_version: str
    detector_ruleset_version: str
    findings: tuple[Finding, ...]
    risk_profile: JsonObject
    risk_contributions: tuple[JsonObject, ...]
    risk_explanation: JsonObject
    policy_decision: PolicyDecision
    timing: JsonObject
    correlation_id: str
    redacted_content: str | None
    request_id: str | None


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ChatCompletion:
    id: str
    created: int
    model: str
    content: str
    finish_reason: Literal["stop", "length"]
    usage: dict[str, int] | None
    request_id: str | None
    input_analysis_id: str | None
    output_analysis_id: str | None
    input_action: Action | None
    output_action: Action | None


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    organization_id: str
    status: IncidentStatus
    severity: IncidentSeverity
    source: Literal["manual", "gateway", "analyze", "playground"]
    title: str
    safe_summary: str
    version: int
    created_at: str
    updated_at: str
    application_id: str | None = None
    environment_id: str | None = None
    assignee_user_id: str | None = None
    action: Action | None = None
    risk_score: int | None = None
    category: str | None = None
    resolved_at: str | None = None
    details: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IncidentPage:
    items: tuple[Incident, ...]
    next_cursor: str | None
    limit: int
    request_id: str | None


@dataclass(frozen=True, slots=True)
class IncidentFilters:
    statuses: tuple[IncidentStatus, ...] = ()
    severities: tuple[IncidentSeverity, ...] = ()
    application_id: str | None = None
    environment_id: str | None = None
    assignee_user_id: str | None = None
    unassigned: bool = False
    source: Literal["manual", "gateway", "analyze", "playground"] | None = None
    action: Action | None = None
    category: str | None = None
    created_from: str | None = None
    created_to: str | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class AnalyticsDashboard:
    filters: JsonObject
    summary: JsonObject
    activity: tuple[JsonObject, ...]
    risk_distribution: tuple[JsonObject, ...]
    threat_categories: tuple[JsonObject, ...]
    top_detectors: tuple[JsonObject, ...]
    policy_actions: tuple[JsonObject, ...]
    applications: tuple[JsonObject, ...]
    environments: tuple[JsonObject, ...]
    providers: tuple[JsonObject, ...]
    incidents: JsonObject
    recent_incidents: tuple[JsonObject, ...]
    query_duration_ms: int
    request_id: str | None


@dataclass(frozen=True, slots=True)
class AIIntelligenceResult:
    request_id: str
    incident_id: str
    task_type: AITaskType
    status: AIStatus
    ai_generated: bool
    context_mode: DisclosureMode
    incident_version: int
    provider_id: str
    provider_name: str
    model: str
    prompt_template_version: str | None
    input_context_version: str
    output_schema_version: str
    content: JsonObject | None
    usage: dict[str, int | None] | None
    error_code: str | None
    created_at: str
    completed_at: str | None
    response_request_id: str | None = None
