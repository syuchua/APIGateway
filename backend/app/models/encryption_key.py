"""
加密密钥 ORM 模型
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from .base import Base


class EncryptionKey(Base):
    """存储对称加密密钥"""

    __tablename__ = "encryption_keys"
    __table_args__ = {"schema": "gateway"}

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    key_material = Column(LargeBinary(96), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    extra = Column(JSONB, nullable=True)

    def touch_rotation(self) -> None:
        """更新轮换时间"""
        self.rotated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.extra or {},
        }


__all__ = ["EncryptionKey"]
