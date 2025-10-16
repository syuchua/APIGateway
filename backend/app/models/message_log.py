"""
消息日志ORM模型
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from .base import Base


class MessageLog(Base):
    """消息日志模型（分区表）"""

    __tablename__ = "message_logs"
    __table_args__ = {"schema": "gateway"}

    # 主键（包含timestamp用于分区）
    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow)

    # 消息信息
    message_id = Column(String(100), nullable=False, index=True)

    # 来源信息
    source_protocol = Column(String(20), nullable=False)
    source_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    source_address = Column(Text, nullable=True)

    # 原始数据
    raw_data = Column(LargeBinary, nullable=True)
    raw_data_size = Column(Integer, nullable=True)

    # 解析后数据
    parsed_data = Column(JSONB, nullable=True)

    # 处理状态
    processing_status = Column(String(20), default="received")

    # 路由信息
    matched_rules = Column(JSONB, nullable=True)
    target_systems = Column(JSONB, nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "source_protocol": self.source_protocol,
            "source_id": str(self.source_id) if self.source_id else None,
            "source_address": self.source_address,
            "raw_data_size": self.raw_data_size,
            "parsed_data": self.parsed_data,
            "processing_status": self.processing_status,
            "matched_rules": self.matched_rules,
            "target_systems": self.target_systems,
            "error_message": self.error_message,
        }

    def __repr__(self):
        return f"<MessageLog(id={self.id}, message_id={self.message_id}, status={self.processing_status})>"


__all__ = ["MessageLog"]
