"""
转发器相关Pydantic Schemas
"""
from typing import Dict, Any, Optional
from enum import Enum

from pydantic import Field, field_validator

from .common import BaseSchema


class HTTPMethod(str, Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ForwardStatus(str, Enum):
    """转发状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"


class HTTPForwarderConfig(BaseSchema):
    """HTTP转发器配置"""
    url: str = Field(..., description="目标URL")
    method: HTTPMethod = Field(default=HTTPMethod.POST, description="HTTP方法")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    timeout: int = Field(default=30, ge=1, le=300, description="超时时间(秒)")
    retry_times: int = Field(default=3, ge=0, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="重试延迟(秒)")
    username: Optional[str] = Field(None, description="HTTP认证用户名")
    password: Optional[str] = Field(None, description="HTTP认证密码")
    verify_ssl: bool = Field(default=True, description="是否验证SSL证书")


class WebSocketForwarderConfig(BaseSchema):
    """WebSocket转发器配置"""
    url: str = Field(..., description="WebSocket服务器URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="连接请求头")
    timeout: int = Field(default=30, ge=1, le=300, description="连接超时时间(秒)")
    retry_times: int = Field(default=3, ge=0, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="重试延迟(秒)")
    ping_interval: int = Field(default=30, ge=1, le=300, description="心跳间隔(秒)")
    ping_timeout: int = Field(default=10, ge=1, le=60, description="心跳超时时间(秒)")
    close_timeout: int = Field(default=10, ge=1, le=60, description="关闭超时时间(秒)")


class TCPForwarderConfig(BaseSchema):
    """TCP转发器配置"""
    host: str = Field(..., description="目标主机地址")
    port: int = Field(..., ge=1, le=65535, description="目标端口")
    timeout: int = Field(default=30, ge=1, le=300, description="连接超时时间(秒)")
    retry_times: int = Field(default=3, ge=0, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="重试延迟(秒)")
    buffer_size: int = Field(default=8192, ge=1024, le=65536, description="缓冲区大小")
    encoding: str = Field(default="utf-8", description="数据编码格式")
    keep_alive: bool = Field(default=True, description="是否保持连接")
    newline: str = Field(default="\n", description="数据行结束符")
    
    @field_validator('newline', mode='before')
    @classmethod
    def preserve_newline(cls, v):
        """保留换行符不被去除"""
        if v is None:
            return "\n"
        return v


class UDPForwarderConfig(BaseSchema):
    """UDP转发器配置"""
    host: str = Field(..., description="目标主机地址")
    port: int = Field(..., ge=1, le=65535, description="目标端口")
    timeout: int = Field(default=5, ge=1, le=60, description="发送超时时间(秒)")
    retry_times: int = Field(default=1, ge=0, le=5, description="重试次数")
    retry_delay: float = Field(default=0.1, ge=0.01, le=5.0, description="重试延迟(秒)")
    buffer_size: int = Field(default=8192, ge=1024, le=65536, description="缓冲区大小")
    encoding: str = Field(default="utf-8", description="数据编码格式")


class MQTTForwarderConfig(BaseSchema):
    """MQTT转发器配置"""
    host: str = Field(..., description="MQTT代理地址")
    port: int = Field(default=1883, ge=1, le=65535, description="MQTT代理端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    topic: str = Field(..., description="发布主题")
    qos: int = Field(default=1, ge=0, le=2, description="服务质量等级")
    retain: bool = Field(default=False, description="是否保留消息")
    client_id: Optional[str] = Field(None, description="客户端ID")
    keepalive: int = Field(default=60, ge=1, le=300, description="保持连接时间(秒)")
    timeout: int = Field(default=10, ge=1, le=60, description="连接超时时间(秒)")
    retry_times: int = Field(default=3, ge=0, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="重试延迟(秒)")
    tls_enabled: bool = Field(default=False, description="是否启用TLS")
    ca_cert: Optional[str] = Field(None, description="CA证书路径")
    cert_file: Optional[str] = Field(None, description="客户端证书路径")
    key_file: Optional[str] = Field(None, description="客户端私钥路径")


class ForwardResult(BaseSchema):
    """转发结果"""
    status: ForwardStatus = Field(..., description="转发状态")
    status_code: Optional[int] = Field(None, description="状态码")
    response_text: Optional[str] = Field(None, description="响应文本")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    duration: float = Field(default=0.0, description="耗时(秒)")


__all__ = [
    "HTTPMethod",
    "ForwardStatus",
    "HTTPForwarderConfig",
    "WebSocketForwarderConfig",
    "TCPForwarderConfig",
    "UDPForwarderConfig",
    "MQTTForwarderConfig",
    "ForwardResult",
]
