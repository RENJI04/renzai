"""UUIDv7 generation compatible with PostgreSQL UUID columns."""

from uuid import UUID

from uuid6 import uuid7


def new_uuid7() -> UUID:
    """Return an RFC UUIDv7 object; IDs are never authorization secrets."""
    return uuid7()
