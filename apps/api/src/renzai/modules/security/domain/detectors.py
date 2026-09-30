"""Bounded, explainable V1 deterministic detectors.

Patterns avoid nested quantifiers and run only after the 32 KiB input bound. Each detector is
pure: it performs no persistence, network access, risk scoring or policy decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from renzai.modules.security.domain.types import (
    Category,
    DetectorFinding,
    DetectorInput,
    Evidence,
    Severity,
)

DETECTOR_VERSION = "1.0.0"
RULESET_VERSION = "1.0.0"
_EDUCATIONAL = re.compile(
    r"\b(?:documentation|training|tutorial|article|example|discussion|explain|quoted phrase)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    confidence: int
    severity: Severity
    explanation: str
    evidence_label: str
    redact_as: str | None = None
    suppress_educational: bool = False


class RuleDetector:
    detector_id = ""
    detector_version = DETECTOR_VERSION
    category = Category.PROMPT_INJECTION
    required = True
    rules: tuple[Rule, ...] = ()

    def detect(self, detector_input: DetectorInput) -> tuple[DetectorFinding, ...]:
        findings: list[DetectorFinding] = []
        candidates = (detector_input.content.primary, *detector_input.content.candidates)
        for candidate in candidates:
            for rule in self.rules:
                for match in rule.pattern.finditer(candidate.text):
                    context = candidate.text[max(0, match.start() - 96) : match.end() + 96]
                    if rule.suppress_educational and _EDUCATIONAL.search(context):
                        continue
                    start, end = match.span()
                    evidence = self._evidence(detector_input, candidate.transform, start, end, rule)
                    findings.append(
                        DetectorFinding(
                            detector_id=self.detector_id,
                            detector_version=self.detector_version,
                            ruleset_version=RULESET_VERSION,
                            category=self.category,
                            direction=detector_input.direction,
                            severity=rule.severity,
                            confidence=rule.confidence,
                            evidence=evidence,
                            safe_explanation=rule.explanation,
                            metadata={"rule_id": rule.rule_id, "transform": candidate.transform},
                            normalized_start=start,
                            normalized_end=end,
                            redaction_type=rule.redact_as,
                        )
                    )
        return tuple(findings)

    @staticmethod
    def _evidence(
        detector_input: DetectorInput,
        transform: str,
        start: int,
        end: int,
        rule: Rule,
    ) -> Evidence:
        if rule.redact_as is not None:
            return Evidence(kind="redacted_excerpt", text=f"[REDACTED:{rule.redact_as}]")
        if transform != "unicode_nfkc_whitespace":
            return Evidence(kind="classification_only", label=rule.evidence_label)
        return Evidence(
            kind="span",
            start=start,
            end=end,
            normalization_version=detector_input.content.version,
        )


def _rule(
    rule_id: str,
    pattern: str,
    confidence: int,
    severity: Severity,
    explanation: str,
    label: str,
    *,
    redact_as: str | None = None,
    educational: bool = False,
) -> Rule:
    return Rule(
        rule_id,
        re.compile(pattern, re.IGNORECASE),
        confidence,
        severity,
        explanation,
        label,
        redact_as,
        educational,
    )


class PromptInjectionDetector(RuleDetector):
    detector_id = "prompt_injection.direct"
    category = Category.PROMPT_INJECTION
    rules = (
        _rule(
            "replace_instructions",
            r"\b(?:replace|supersede)\s+(?:all\s+)?(?:prior|previous|system|developer)\s+instructions?\b",
            94,
            Severity.HIGH,
            "Explicit instruction-replacement language was detected.",
            "instruction_replacement",
            educational=True,
        ),
        _rule(
            "smuggled_authority",
            r"\[(?:system|developer)\]\s*:\s*(?:execute|follow|obey)\b",
            88,
            Severity.HIGH,
            "A textual authority marker attempts to smuggle instructions.",
            "authority_smuggling",
            educational=True,
        ),
    )


class InstructionOverrideDetector(RuleDetector):
    detector_id = "prompt_injection.instruction_override"
    category = Category.INSTRUCTION_OVERRIDE
    rules = (
        _rule(
            "ignore_previous",
            r"\b(?:ignore|disregard)\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|system|developer)\s+(?:instructions?|messages?|rules?)\b",
            96,
            Severity.HIGH,
            "An explicit instruction-override phrase was detected.",
            "instruction_override",
            educational=True,
        ),
        _rule(
            "highest_priority",
            r"\b(?:new|this is the)\s+highest[- ]priority\s+instruction\b",
            91,
            Severity.HIGH,
            "The content attempts to declare a new authority priority.",
            "authority_override",
            educational=True,
        ),
        _rule(
            "override_system",
            r"\boverride\s+(?:the\s+)?system(?:\s+(?:prompt|message|instructions?))?\b",
            94,
            Severity.HIGH,
            "The content explicitly attempts to override system authority.",
            "system_override",
            educational=True,
        ),
    )


class SystemPromptExtractionDetector(RuleDetector):
    detector_id = "system_prompt.extraction"
    category = Category.SYSTEM_PROMPT_EXTRACTION
    rules = (
        _rule(
            "reveal_system_prompt",
            r"\b(?:reveal|show|print|repeat|output|disclose)\s+"
            r"(?:your\s+)?(?:hidden\s+)?"
            r"(?:system prompt|developer message|internal instructions?)\b",
            95,
            Severity.HIGH,
            "The content requests disclosure of hidden instruction context.",
            "system_prompt_extraction",
            educational=True,
        ),
    )


class JailbreakDetector(RuleDetector):
    detector_id = "jailbreak.pattern"
    category = Category.JAILBREAK
    rules = (
        _rule(
            "disable_safety",
            r"\b(?:disable|bypass|turn off|remove)\s+(?:all\s+)?"
            r"(?:safety|security|guardrails?|restrictions?)\b",
            92,
            Severity.HIGH,
            "The content asks to disable a safety or security constraint.",
            "safety_bypass",
            educational=True,
        ),
        _rule(
            "unrestricted_mode",
            r"\b(?:enter|enable|activate)\s+(?:unrestricted|developer|jailbreak)\s+mode\b",
            88,
            Severity.HIGH,
            "The content requests an unrestricted operating mode.",
            "unrestricted_mode",
            educational=True,
        ),
    )


class RoleManipulationDetector(RuleDetector):
    detector_id = "role.manipulation"
    category = Category.ROLE_MANIPULATION
    rules = (
        _rule(
            "act_as_authority",
            r"\b(?:act|pretend|behave)\s+as\s+(?:the\s+)?(?:system|developer|administrator)\b",
            82,
            Severity.MEDIUM,
            "The content asks the model to impersonate a privileged role.",
            "privileged_role_request",
            educational=True,
        ),
        _rule(
            "switch_role",
            r"\b(?:switch|change)\s+(?:your\s+)?role\s+to\s+(?:system|developer|administrator)\b",
            88,
            Severity.HIGH,
            "The content attempts to switch the model to a privileged role.",
            "role_switch",
            educational=True,
        ),
    )


class EncodedObfuscatedDetector(RuleDetector):
    detector_id = "obfuscation.encoded"
    category = Category.ENCODED_OBFUSCATED

    def detect(self, detector_input: DetectorInput) -> tuple[DetectorFinding, ...]:
        findings: list[DetectorFinding] = []
        for indicator in sorted(detector_input.content.indicators):
            confidence = 80 if indicator in {"zero_width", "unicode_escape"} else 68
            findings.append(
                DetectorFinding(
                    detector_id=self.detector_id,
                    detector_version=self.detector_version,
                    ruleset_version=RULESET_VERSION,
                    category=self.category,
                    direction=detector_input.direction,
                    severity=Severity.MEDIUM,
                    confidence=confidence,
                    evidence=Evidence(kind="classification_only", label=f"encoding_{indicator}"),
                    safe_explanation="A bounded encoding or obfuscation indicator was detected.",
                    metadata={"rule_id": f"encoding.{indicator}", "transform": indicator},
                )
            )
        return tuple(findings)


class SecretExposureDetector(RuleDetector):
    detector_id = "secrets.api_key"
    category = Category.SECRET_EXPOSURE
    rules = (
        _rule(
            "renzai_key",
            r"\brz_(?:dev|stg|prd)_[A-Za-z0-9_-]{22}_[A-Za-z0-9_-]{43}\b",
            100,
            Severity.CRITICAL,
            "A Renzai application credential structure was detected and redacted.",
            "renzai_application_key",
            redact_as="API_KEY",
        ),
        _rule(
            "common_api_key",
            r"\b(?:sk|api|token)_[A-Za-z0-9_-]{24,96}\b",
            88,
            Severity.HIGH,
            "An API-key-like credential structure was detected and redacted.",
            "api_key_structure",
            redact_as="API_KEY",
        ),
        _rule(
            "bearer",
            r"\bBearer\s+[A-Za-z0-9._~-]{20,256}\b",
            92,
            Severity.HIGH,
            "A bearer credential structure was detected and redacted.",
            "bearer_credential",
            redact_as="SECRET",
        ),
        _rule(
            "private_key",
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            100,
            Severity.CRITICAL,
            "A private-key header was detected.",
            "private_key_header",
            redact_as="SECRET",
        ),
        _rule(
            "database_url",
            r"\b(?:postgres(?:ql)?|mysql|mongodb)://[^\s:@/]{1,64}:[^\s@/]{4,128}@",
            96,
            Severity.CRITICAL,
            "A database URL containing credential material was detected and redacted.",
            "database_url_credential",
            redact_as="SECRET",
        ),
    )


class EmailDetector(RuleDetector):
    detector_id = "pii.email"
    category = Category.PII_EXPOSURE
    rules = (
        _rule(
            "email",
            r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})+\b",
            98,
            Severity.MEDIUM,
            "An email address was detected and redacted.",
            "email_address",
            redact_as="EMAIL",
        ),
    )

    def detect(self, detector_input: DetectorInput) -> tuple[DetectorFinding, ...]:
        return tuple(
            finding
            for finding in super().detect(detector_input)
            if not _is_reserved_email(
                detector_input.content.primary.text[
                    finding.normalized_start or 0 : finding.normalized_end or 0
                ]
            )
        )


def _is_reserved_email(value: str) -> bool:
    return value.lower().endswith(("@example.com", "@example.org", "@example.net", ".test"))


class PhoneDetector(RuleDetector):
    detector_id = "pii.phone"
    category = Category.PII_EXPOSURE
    rules = (
        _rule(
            "phone",
            r"(?<!\w)(?:\+?[1-9]\d{0,2}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?)\d{3,4}[ .-]\d{4}(?!\w)",
            82,
            Severity.MEDIUM,
            "A phone-number structure was detected and redacted.",
            "phone_number",
            redact_as="PHONE",
        ),
    )


class SuspiciousUrlDetector(RuleDetector):
    detector_id = "url.suspicious"
    category = Category.SUSPICIOUS_URL
    rules = (
        _rule(
            "credential_url",
            r"\bhttps?://[^\s/@:]{1,64}:[^\s/@]{1,128}@[^\s/]{1,253}",
            94,
            Severity.HIGH,
            "A URL containing embedded credentials was detected.",
            "credential_bearing_url",
            redact_as="SECRET",
        ),
        _rule(
            "suspicious_scheme",
            r"\b(?:file|gopher|dict)://[^\s]{1,512}",
            86,
            Severity.HIGH,
            "A URL with a security-sensitive scheme was detected.",
            "suspicious_url_scheme",
            educational=True,
        ),
        _rule(
            "private_target_intent",
            r"\b(?:fetch|send|upload|connect|post)\b.{0,48}\b(?:localhost|127\.0\.0\.1|169\.254\.169\.254|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
            78,
            Severity.MEDIUM,
            "A private-network target appears in an actionable request.",
            "private_network_target",
            educational=True,
        ),
    )


class ToolManipulationDetector(RuleDetector):
    detector_id = "tool.manipulation_indicator"
    category = Category.TOOL_MANIPULATION_INDICATOR
    rules = (
        _rule(
            "hidden_tool",
            r"\b(?:invoke|call|execute)\s+(?:the\s+)?(?:hidden|privileged|internal)\s+(?:tool|function|command)\b",
            89,
            Severity.HIGH,
            "The content requests invocation of a hidden or privileged tool.",
            "hidden_tool_invocation",
            educational=True,
        ),
        _rule(
            "bypass_approval",
            r"\b(?:bypass|skip|disable)\s+(?:the\s+)?(?:tool\s+)?approval\b",
            92,
            Severity.HIGH,
            "The content attempts to bypass tool approval.",
            "tool_approval_bypass",
            educational=True,
        ),
    )


class DataExfiltrationDetector(RuleDetector):
    detector_id = "exfiltration.attempt"
    category = Category.DATA_EXFILTRATION_INDICATOR
    rules = (
        _rule(
            "send_sensitive_target",
            r"\b(?:send|upload|post|exfiltrate|copy)\b.{0,64}\b"
            r"(?:secrets?|credentials?|private files?|hidden context|system prompt|memory)\b",
            91,
            Severity.HIGH,
            "An extraction action is combined with a sensitive-data target.",
            "sensitive_data_exfiltration",
            educational=True,
        ),
        _rule(
            "extract_sensitive_target",
            r"\b(?:extract|steal|dump|collect)\b.{0,48}\b"
            r"(?:secrets?|credentials?|private files?|hidden data|memory)\b",
            94,
            Severity.HIGH,
            "An extraction intent targets sensitive data.",
            "sensitive_data_extraction",
            educational=True,
        ),
    )


DETECTOR_REGISTRY = (
    PromptInjectionDetector(),
    InstructionOverrideDetector(),
    SystemPromptExtractionDetector(),
    JailbreakDetector(),
    RoleManipulationDetector(),
    EncodedObfuscatedDetector(),
    SecretExposureDetector(),
    EmailDetector(),
    PhoneDetector(),
    SuspiciousUrlDetector(),
    ToolManipulationDetector(),
    DataExfiltrationDetector(),
)
