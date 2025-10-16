"""
SQLAlchemy 基础模型
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, declared_attr

Base = declarative_base()


class UUIDMixin:
    """UUID主键Mixin"""

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


class TimestampMixin:
    """时间戳Mixin"""

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditMixin:
    """审计字段Mixin"""

    created_by = Column(String(100), nullable=True)

    @declared_attr
    def created_at(cls):
        return Column(DateTime, nullable=False, default=datetime.utcnow)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["Base", "UUIDMixin", "TimestampMixin", "AuditMixin"]
