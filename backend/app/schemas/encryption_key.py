"""加密密钥 Schemas"""
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID

from pydantic import Field

from .common import BaseSchema, UUIDMixin, TimestampMixin


class EncryptionKeyBase(BaseSchema):
    """密钥基础信息"""

    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    description: Optional[str] = Field(None, description="密钥描述")
    metadata: Optional[Dict[str, str]] = Field(None, description="附加元数据")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class EncryptionKeyCreate(EncryptionKeyBase):
    key_material: Optional[str] = Field(None, description="Base64编码的密钥原文，不提供时自动生成")
    is_active: bool = Field(default=False, description="创建后是否激活")


class EncryptionKeyUpdate(BaseSchema):
    description: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    expires_at: Optional[datetime] = None


class EncryptionKeyResponse(UUIDMixin, TimestampMixin, EncryptionKeyBase):
    is_active: bool
    rotated_at: Optional[datetime] = None


__all__ = [
    "EncryptionKeyCreate",
    "EncryptionKeyUpdate",
    "EncryptionKeyResponse",
]
