"""
用户ORM模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text

from .base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    """用户模型"""

    __tablename__ = "users"
    __table_args__ = {"schema": "gateway"}

    username = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    full_name = Column(String(128), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    avatar = Column(Text, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    def mark_login(self) -> None:
        """更新最后登录时间"""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


__all__ = ["User"]
