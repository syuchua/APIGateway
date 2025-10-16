"""
数据源ORM模型
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDMixin, AuditMixin


class DataSource(Base, UUIDMixin, AuditMixin):
    """数据源模型"""

    __tablename__ = "data_sources"
    __table_args__ = {"schema": "gateway"}

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    protocol_type = Column(String(20), nullable=False)  # udp, http, websocket, tcp, mqtt
    is_active = Column(Boolean, default=True, nullable=False)

    # 连接配置
    connection_config = Column(JSONB, nullable=False)

    # 帧格式
    frame_schema_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # 统计信息
    total_messages = Column(BigInteger, default=0)
    last_message_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "protocol_type": self.protocol_type,
            "is_active": self.is_active,
            "connection_config": self.connection_config,
            "frame_schema_id": str(self.frame_schema_id) if self.frame_schema_id else None,
            "total_messages": self.total_messages,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.name}, protocol={self.protocol_type})>"


__all__ = ["DataSource"]
