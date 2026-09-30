"""Budgeted, deterministic Unicode and encoding normalization."""

from __future__ import annotations

import base64
import binascii
import html
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote

from renzai.modules.security.domain.types import NormalizedCandidate, NormalizedContent

NORMALIZATION_VERSION = "1.0.0"
ZERO_WIDTH = frozenset({"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"})
BASE64_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/=_-])([A-Za-z0-9+/_-]{24,2048}={0,2})(?![A-Za-z0-9+/=_-])"
)
UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


class NormalizationLimitError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizationBudget:
    max_input_bytes: int = 32 * 1024
    max_candidates: int = 8
    max_candidate_chars: int = 4096
    max_expansion_factor: int = 4
    max_decode_depth: int = 1


def _primary(text: str) -> tuple[str, tuple[int, ...]]:
    output: list[str] = []
    source_map: list[int] = []
    previous_space = False
    for original_index, character in enumerate(text):
        if character in ZERO_WIDTH:
            continue
        expanded = unicodedata.normalize("NFKC", character)
        for normalized in expanded:
            is_space = normalized.isspace()
            if is_space and previous_space:
                continue
            output.append(" " if is_space else normalized)
            source_map.append(original_index)
            previous_space = is_space
    return "".join(output), tuple(source_map)


def _identity_map(value: str) -> tuple[int, ...]:
    return tuple(range(len(value)))


def _decode_unicode_escapes(value: str) -> str:
    return UNICODE_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), value)


def normalize(text: str, budget: NormalizationBudget | None = None) -> NormalizedContent:
    limits = budget or NormalizationBudget()
    byte_count = len(text.encode("utf-8"))
    if byte_count > limits.max_input_bytes:
        raise NormalizationLimitError("input exceeds configured UTF-8 byte limit")

    primary_text, primary_map = _primary(text)
    primary = NormalizedCandidate(primary_text, "unicode_nfkc_whitespace", primary_map)
    candidates: list[NormalizedCandidate] = []
    indicators: set[str] = set()
    if any(character in ZERO_WIDTH for character in text):
        indicators.add("zero_width")

    # Every transform is single-pass, bounded and never recursively feeds another transform.
    transforms: tuple[tuple[str, bool, object], ...] = (
        ("percent", "%" in text, unquote),
        ("html_entity", "&" in text and ";" in text, html.unescape),
        ("unicode_escape", "\\u" in text, _decode_unicode_escapes),
    )
    seen = {primary_text}
    for name, applicable, transform in transforms:
        if not applicable or len(candidates) >= limits.max_candidates:
            continue
        decoded = transform(text)  # type: ignore[operator]
        if not isinstance(decoded, str) or decoded == text or decoded in seen:
            continue
        if (
            len(decoded) > limits.max_candidate_chars
            or len(decoded) > max(1, len(text)) * limits.max_expansion_factor
        ):
            continue
        normalized, _ = _primary(decoded)
        if normalized and normalized not in seen:
            candidates.append(NormalizedCandidate(normalized, name, _identity_map(normalized)))
            indicators.add(name)
            seen.add(normalized)

    for match in BASE64_CANDIDATE.finditer(text):
        if len(candidates) >= limits.max_candidates:
            break
        token = match.group(1)
        if len(token) > limits.max_candidate_chars:
            continue
        try:
            padding = "=" * (-len(token) % 4)
            raw = base64.urlsafe_b64decode(token + padding)
            decoded = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if (
            not decoded.isprintable()
            or len(decoded) > max(1, len(token)) * limits.max_expansion_factor
        ):
            continue
        normalized, _ = _primary(decoded)
        if normalized and normalized not in seen:
            candidates.append(
                NormalizedCandidate(normalized, "base64", tuple(match.start() for _ in normalized))
            )
            indicators.add("base64")
            seen.add(normalized)

    return NormalizedContent(
        original=text,
        primary=primary,
        candidates=tuple(candidates),
        version=NORMALIZATION_VERSION,
        indicators=frozenset(indicators),
    )
