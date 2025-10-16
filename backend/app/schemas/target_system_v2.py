"""
目标系统相关Pydantic Schemas (重构版 - 嵌套config结构 + auth_config)
"""
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field, field_validator

from .common import BaseSchema, TimestampMixin, UUIDMixin, ProtocolType


class EndpointConfig(BaseSchema):
    """端点配置Schema"""
    target_address: str = Field(..., description="目标地址")
    target_port: int = Field(..., ge=1, le=65535, description="目标端口")
    endpoint_path: str = Field(default="/", description="端点路径（如 /api/data）")
    use_ssl: bool = Field(default=False, description="是否使用SSL/TLS")


class AuthConfig(BaseSchema):
    """认证配置Schema"""
    auth_type: str = Field(..., description="认证类型 (basic/bearer/api_key/custom/none)")

    # Basic Auth
    username: Optional[str] = Field(None, description="用户名（Basic Auth）")
    password: Optional[str] = Field(None, description="密码（Basic Auth）")

    # Bearer Token
    token: Optional[str] = Field(None, description="Bearer Token")

    # API Key
    api_key: Optional[str] = Field(None, description="API Key")
    api_key_header: Optional[str] = Field(default="X-API-Key", description="API Key请求头名称")

    # Custom Headers
    custom_headers: Optional[Dict[str, str]] = Field(None, description="自定义认证请求头")


class ForwarderConfig(BaseSchema):
    """转发配置Schema"""
    timeout: int = Field(default=30, ge=1, description="超时时间（秒）")
    retry_count: int = Field(default=3, ge=0, description="重试次数")
    batch_size: int = Field(default=1, ge=1, description="批量发送大小")
    compression: bool = Field(default=False, description="是否启用压缩")
    encryption: Optional[Dict[str, Any]] = Field(default=None, description="加密配置")


class TargetSystemCreate(BaseSchema):
    """创建目标系统Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="目标系统名称")
    description: Optional[str] = Field(None, description="目标系统描述")
    is_active: bool = Field(default=True, description="是否启用目标系统")

    # 协议配置
    protocol_type: ProtocolType = Field(..., description="协议类型")

    # 嵌套配置对象
    endpoint_config: EndpointConfig = Field(..., description="端点配置")
    auth_config: Optional[AuthConfig] = Field(None, description="认证配置")
    forwarder_config: ForwarderConfig = Field(
        default_factory=ForwarderConfig,
        description="转发配置"
    )

    # 数据转换配置（可选）
    transform_rules: Optional[Dict[str, Any]] = Field(None, description="数据转换规则")

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
    endpoint_config: Optional[EndpointConfig] = None
    auth_config: Optional[AuthConfig] = None
    forwarder_config: Optional[ForwarderConfig] = None
    transform_rules: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TargetSystemResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """目标系统响应Schema"""
    name: str
    description: Optional[str] = None
    protocol_type: ProtocolType
    status: Optional[str] = None

    # 嵌套配置对象
    endpoint_config: EndpointConfig
    auth_config: Optional[AuthConfig] = None
    forwarder_config: ForwarderConfig

    # 数据转换配置
    transform_rules: Optional[Dict[str, Any]] = None

    is_active: bool


__all__ = [
    "EndpointConfig",
    "AuthConfig",
    "ForwarderConfig",
    "TargetSystemCreate",
    "TargetSystemUpdate",
    "TargetSystemResponse",
]
