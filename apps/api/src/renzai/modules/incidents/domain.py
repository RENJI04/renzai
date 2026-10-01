"""Framework-independent incident lifecycle, RBAC, and safe text rules."""

from __future__ import annotations

from enum import StrEnum

from renzai.modules.memberships.domain import MembershipRole


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


TERMINAL_STATUSES = frozenset(
    {IncidentStatus.RESOLVED, IncidentStatus.IGNORED, IncidentStatus.FALSE_POSITIVE}
)
TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.OPEN: frozenset(
        {
            IncidentStatus.INVESTIGATING,
            IncidentStatus.RESOLVED,
            IncidentStatus.IGNORED,
            IncidentStatus.FALSE_POSITIVE,
        }
    ),
    IncidentStatus.INVESTIGATING: frozenset(
        {
            IncidentStatus.OPEN,
            IncidentStatus.RESOLVED,
            IncidentStatus.IGNORED,
            IncidentStatus.FALSE_POSITIVE,
        }
    ),
    IncidentStatus.RESOLVED: frozenset({IncidentStatus.INVESTIGATING}),
    IncidentStatus.IGNORED: frozenset({IncidentStatus.INVESTIGATING}),
    IncidentStatus.FALSE_POSITIVE: frozenset({IncidentStatus.INVESTIGATING}),
}

INCIDENT_EDITORS = frozenset(
    {MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.SECURITY_ANALYST}
)
INCIDENT_COMMENTERS = INCIDENT_EDITORS | {MembershipRole.DEVELOPER}


class InvalidIncidentTransition(ValueError):
    pass


def validate_transition(
    current: IncidentStatus, target: IncidentStatus, reason: str | None
) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidIncidentTransition(f"cannot transition {current} to {target}")
    if current in TERMINAL_STATUSES and target is IncidentStatus.INVESTIGATING and not reason:
        raise InvalidIncidentTransition("reopening a terminal incident requires a reason")


def can_edit_incident(role: MembershipRole) -> bool:
    return role in INCIDENT_EDITORS


def can_comment_on_incident(role: MembershipRole) -> bool:
    return role in INCIDENT_COMMENTERS


def normalize_plain_text(value: str, *, maximum: int, multiline: bool = True) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum:
        raise ValueError("text length is invalid")
    if any(ord(character) < 32 and character not in {"\n", "\r", "\t"} for character in cleaned):
        raise ValueError("text contains control characters")
    if not multiline and any(character in cleaned for character in "\r\n"):
        raise ValueError("text must be one line")
    return cleaned


def automatic_title(severity: IncidentSeverity, category: str | None, action: str) -> str:
    threat = (category or "security event").replace("_", " ")
    suffix = "requires review" if action == "require_review" else "blocked"
    return f"{severity.value.title()} {threat} {suffix}"


def automatic_summary(
    *, source: str, direction: str, action: str, category: str | None, risk_score: int
) -> str:
    threat = (category or "security_event").replace("_", " ")
    return f"{source} {direction} {action}; {threat}; risk {risk_score}/100."
