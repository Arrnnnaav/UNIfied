"""Portable column types: UUID and embedding vectors that work on Postgres (+pgvector) and SQLite (tests)."""
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID

            return dialect.type_descriptor(UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class VectorPortable(TypeDecorator):
    """pgvector Vector on Postgres, JSON list elsewhere (tests)."""

    impl = sa.JSON
    cache_ok = True

    def __init__(self, dim: int = 384):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(sa.JSON())

    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name == "postgresql":
            import numpy as np

            if isinstance(value, np.ndarray):
                return value.tolist()
        return value
