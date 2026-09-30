"""Declarative base reserved for later domain-owned models."""

from sqlalchemy.orm import DeclarativeBase

from renzai.db.metadata import metadata


class Base(DeclarativeBase):
    metadata = metadata
