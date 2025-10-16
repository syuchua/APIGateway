"""
目标系统ORM模型
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, UUIDMixin, AuditMixin


class TargetSystem(Base, UUIDMixin, AuditMixin):
    """目标系统模型"""

    __tablename__ = "target_systems"
    __table_args__ = {"schema": "gateway"}

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    protocol_type = Column(String(20), nullable=False)  # http, websocket, tcp, udp, mqtt
    endpoint = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # 转发器配置
    forwarder_config = Column(JSONB, nullable=False)

    # 数据转换配置
    transform_config = Column(JSONB, nullable=True)

    # 统计信息
    total_forwarded = Column(BigInteger, default=0)
    total_failed = Column(BigInteger, default=0)
    last_forward_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "protocol_type": self.protocol_type,
            "endpoint": self.endpoint,
            "is_active": self.is_active,
            "forwarder_config": self.forwarder_config,
            "transform_config": self.transform_config,
            "total_forwarded": self.total_forwarded,
            "total_failed": self.total_failed,
            "last_forward_at": self.last_forward_at.isoformat() if self.last_forward_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<TargetSystem(id={self.id}, name={self.name}, protocol={self.protocol_type})>"


__all__ = ["TargetSystem"]
