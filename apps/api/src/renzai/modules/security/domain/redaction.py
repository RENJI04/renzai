"""Deterministic typed redaction with explicit overlap precedence."""

from __future__ import annotations

from dataclasses import dataclass

PLACEHOLDERS = {
    "EMAIL": "[REDACTED:EMAIL]",
    "PHONE": "[REDACTED:PHONE]",
    "API_KEY": "[REDACTED:API_KEY]",
    "SECRET": "[REDACTED:SECRET]",
}
_PRIORITY = {"SECRET": 4, "API_KEY": 3, "EMAIL": 2, "PHONE": 1}


@dataclass(frozen=True, slots=True)
class RedactionSpan:
    start: int
    end: int
    kind: str


def select_redaction_spans(spans: list[RedactionSpan]) -> tuple[RedactionSpan, ...]:
    valid = [span for span in spans if span.kind in PLACEHOLDERS and span.start < span.end]
    ordered = sorted(valid, key=lambda item: (item.start, -item.end, -_PRIORITY[item.kind]))
    selected: list[RedactionSpan] = []
    for candidate in ordered:
        overlapping = [
            item for item in selected if candidate.start < item.end and item.start < candidate.end
        ]
        if not overlapping:
            selected.append(candidate)
            continue
        strongest = max(
            [candidate, *overlapping],
            key=lambda item: (_PRIORITY[item.kind], item.end - item.start, -item.start),
        )
        selected = [item for item in selected if item not in overlapping]
        selected.append(strongest)
    return tuple(sorted(selected, key=lambda item: (item.start, item.end, item.kind)))


def redact(text: str, spans: list[RedactionSpan]) -> str:
    selected = select_redaction_spans(spans)
    output: list[str] = []
    cursor = 0
    for span in selected:
        output.append(text[cursor : span.start])
        output.append(PLACEHOLDERS[span.kind])
        cursor = span.end
    output.append(text[cursor:])
    return "".join(output)
