"""
帧格式ORM模型
"""
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, UUIDMixin, AuditMixin


class FrameSchema(Base, UUIDMixin, AuditMixin):
    """帧格式模型"""

    __tablename__ = "frame_schemas"
    __table_args__ = {"schema": "gateway"}

    # 基本信息
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)

    # 协议和类型
    protocol_type = Column(String(20), nullable=False)  # udp, tcp
    frame_type = Column(String(20), nullable=False)  # fixed, variable, delimited

    # 帧结构
    total_length = Column(Integer, nullable=True)  # 固定长度帧

    # 字段定义
    fields = Column(JSONB, nullable=False)

    # 校验配置
    checksum = Column(JSONB, nullable=True)

    # 状态
    is_published = Column(Boolean, default=False, nullable=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "protocol_type": self.protocol_type,
            "frame_type": self.frame_type,
            "total_length": self.total_length,
            "fields": self.fields,
            "checksum": self.checksum,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<FrameSchema(id={self.id}, name={self.name}, version={self.version})>"


__all__ = ["FrameSchema"]
