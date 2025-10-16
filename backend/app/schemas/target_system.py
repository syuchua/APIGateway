"""
目标系统相关Pydantic Schemas
"""
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field, field_validator

from .common import BaseSchema, TimestampMixin, UUIDMixin, ProtocolType


class TargetSystemCreate(BaseSchema):
    """创建目标系统Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="目标系统名称")
    description: Optional[str] = Field(None, description="目标系统描述")

    # 协议配置
    protocol_type: ProtocolType = Field(..., description="协议类型")
    target_address: str = Field(..., description="目标地址")
    target_port: int = Field(..., ge=1, le=65535, description="目标端口")
    endpoint_path: str = Field(default="/", description="端点路径（如 /api/data）")

    # 转发配置
    timeout: int = Field(default=30, ge=1, description="超时时间（秒）")
    retry_count: int = Field(default=3, ge=0, description="重试次数")
    batch_size: int = Field(default=1, ge=1, description="批量发送大小")

    # 数据转换配置（可选）
    transform_config: Optional[Dict[str, Any]] = Field(None, description="数据转换配置")

    @field_validator('protocol_type', mode='before')
    @classmethod
    def normalize_protocol_type(cls, v):
        """将协议类型转换为大写"""
        if isinstance(v, str):
            return v.upper()
        return v


class TargetSystemUpdate(BaseSchema):
    """更新目标系统Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    target_address: Optional[str] = None
    target_port: Optional[int] = Field(None, ge=1, le=65535)
    endpoint_path: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=1)
    retry_count: Optional[int] = Field(None, ge=0)
    batch_size: Optional[int] = Field(None, ge=1)
    transform_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TargetSystemResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """目标系统响应Schema"""
    name: str
    description: Optional[str] = None
    protocol_type: ProtocolType
    target_address: str
    target_port: int
    endpoint_path: str
    is_active: bool

    # 转发配置
    timeout: int
    retry_count: int
    batch_size: int

    # 数据转换配置
    transform_config: Optional[Dict[str, Any]] = None

    # 新版嵌套配置透传
    forwarder_config: Dict[str, Any] = Field(default_factory=dict, description="原始转发配置")
    auth_config: Optional[Dict[str, Any]] = Field(default=None, description="认证配置")


__all__ = [
    "TargetSystemCreate",
    "TargetSystemUpdate",
    "TargetSystemResponse",
]
