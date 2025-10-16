"""
数据源相关Pydantic Schemas (重构版 - 嵌套config结构)
"""
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from .common import BaseSchema, TimestampMixin, UUIDMixin, ProtocolType


class ConnectionConfig(BaseSchema):
    """连接配置Schema"""
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        from_attributes=True,
    )
    listen_address: str = Field(default="0.0.0.0", description="监听地址")
    listen_port: int = Field(..., ge=1, le=65535, description="监听端口")
    max_connections: int = Field(default=100, ge=1, description="最大连接数")
    timeout_seconds: int = Field(default=30, ge=1, description="超时时间（秒）")
    buffer_size: int = Field(default=8192, ge=512, description="缓冲区大小")


class ParseConfig(BaseSchema):
    """解析配置Schema"""
    auto_parse: bool = Field(default=True, description="是否自动解析")
    frame_schema_id: Optional[UUID] = Field(None, description="帧格式ID")
    parse_options: Optional[Dict[str, Any]] = Field(None, description="解析选项")


class DataSourceCreate(BaseSchema):
    """创建数据源Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    description: Optional[str] = Field(None, description="数据源描述")

    # 协议配置
    protocol_type: ProtocolType = Field(..., description="协议类型")

    # 嵌套配置对象
    connection_config: ConnectionConfig = Field(..., description="连接配置")
    parse_config: Optional[ParseConfig] = Field(
        default_factory=lambda: ParseConfig(auto_parse=True),
        description="解析配置"
    )

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
    connection_config: Optional[ConnectionConfig] = None
    parse_config: Optional[ParseConfig] = None
    is_active: Optional[bool] = None


class DataSourceResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """数据源响应Schema"""
    name: str
    description: Optional[str] = None
    protocol_type: ProtocolType

    # 嵌套配置对象
    connection_config: ConnectionConfig
    parse_config: ParseConfig

    is_active: bool


__all__ = [
    "ConnectionConfig",
    "ParseConfig",
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
]
