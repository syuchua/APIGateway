"""
转发日志ORM模型
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from .base import Base, UUIDMixin


class ForwardLog(Base, UUIDMixin):
    """转发日志模型"""

    __tablename__ = "forward_logs"
    __table_args__ = {"schema": "gateway"}

    # 关联信息
    message_id = Column(String(100), nullable=False, index=True)
    target_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 转发数据
    forward_data = Column(JSONB, nullable=True)

    # 转发结果
    status = Column(String(20), nullable=False)  # success, failed, pending, retrying
    retry_count = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "message_id": self.message_id,
            "target_id": str(self.target_id),
            "timestamp": self.timestamp.isoformat(),
            "forward_data": self.forward_data,
            "status": self.status,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }

    def __repr__(self):
        return f"<ForwardLog(id={self.id}, message_id={self.message_id}, status={self.status})>"


__all__ = ["ForwardLog"]
