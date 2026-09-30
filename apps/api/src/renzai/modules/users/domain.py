"""Framework-free user identity rules."""

import re
import unicodedata
from enum import StrEnum

from renzai.core.errors import ValidationError


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


def normalize_email(email: str) -> str:
    normalized = unicodedata.normalize("NFKC", email).strip().casefold()
    if len(normalized) > 320 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise ValidationError(details={"fields": ["email"]})
    return normalized


def validate_password(password: str) -> None:
    fields: list[str] = []
    if len(password) < 12 or len(password) > 256:
        fields.append("password")
    if not any(character.isalpha() for character in password):
        fields.append("password")
    if not any(character.isdigit() for character in password):
        fields.append("password")
    if fields:
        raise ValidationError(details={"fields": sorted(set(fields))})
