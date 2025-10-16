"""
数据源相关Pydantic Schemas
"""
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from .common import BaseSchema, TimestampMixin, UUIDMixin, ProtocolType


class DataSourceCreate(BaseSchema):
    """创建数据源Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    description: Optional[str] = Field(None, description="数据源描述")

    # 协议配置
    protocol_type: ProtocolType = Field(..., description="协议类型")
    listen_address: str = Field(default="0.0.0.0", description="监听地址")
    listen_port: int = Field(..., ge=1, le=65535, description="监听端口")

    # 帧格式
    frame_schema_id: Optional[UUID] = Field(None, description="帧格式ID")
    auto_parse: bool = Field(default=True, description="是否自动解析")

    # 连接设置
    max_connections: int = Field(default=100, ge=1, description="最大连接数")
    timeout_seconds: int = Field(default=30, ge=1, description="超时时间（秒）")
    buffer_size: int = Field(default=8192, ge=512, description="缓冲区大小")

    @field_validator('protocol_type', mode='before')
    @classmethod
    def normalize_protocol_type(cls, v):
        """将协议类型转换为大写"""
        if isinstance(v, str):
            return v.upper()
        return v


class DataSourceUpdate(BaseSchema):
    """更新数据源Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    listen_address: Optional[str] = None
    listen_port: Optional[int] = Field(None, ge=1, le=65535)
    frame_schema_id: Optional[UUID] = None
    auto_parse: Optional[bool] = None
    max_connections: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    buffer_size: Optional[int] = Field(None, ge=512)
    is_active: Optional[bool] = None


class DataSourceResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """数据源响应Schema"""
    name: str
    description: Optional[str]
    protocol_type: ProtocolType
    listen_address: str
    listen_port: int
    frame_schema_id: Optional[UUID]
    auto_parse: bool
    max_connections: int
    timeout_seconds: int
    buffer_size: int
    is_active: bool


__all__ = [
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
]