"""Organization value rules."""

import re

from renzai.core.errors import ValidationError


def normalize_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?", normalized):
        raise ValidationError(details={"fields": ["slug"]})
    return normalized


def normalize_name(name: str) -> str:
    normalized = " ".join(name.split())
    if not 2 <= len(normalized) <= 120:
        raise ValidationError(details={"fields": ["name"]})
    return normalized
