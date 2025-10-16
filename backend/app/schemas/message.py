"""
消息相关Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import Field

from .common import BaseSchema, ProtocolType, MessageStatus


class EventBusMessage(BaseSchema):
    """EventBus消息Schema"""
    message_id: str = Field(default_factory=lambda: str(uuid4()), description="消息唯一标识")
    topic: str = Field(..., description="消息主题，大写字母+下划线格式")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")
    source: Optional[str] = Field(None, description="消息来源标识")
    data: Dict[str, Any] = Field(..., description="消息数据")
    trace_id: Optional[str] = Field(None, description="链路追踪ID")


class UnifiedMessage(BaseSchema):
    """统一消息Schema"""
    message_id: str = Field(default_factory=lambda: str(uuid4()), description="消息唯一标识")
    timestamp: datetime = Field(default_factory=datetime.now, description="接收时间戳")
    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="链路追踪ID")

    # 来源信息
    source_protocol: ProtocolType = Field(..., description="来源协议类型")
    source_id: str = Field(..., description="来源标识（数据源ID）")
    source_address: Optional[str] = Field(None, description="来源地址")
    source_port: Optional[int] = Field(None, description="来源端口")

    # 数据内容
    raw_data: bytes = Field(..., description="原始数据")
    data_size: int = Field(..., description="数据大小（字节）")
    parsed_data: Optional[Dict[str, Any]] = Field(None, description="解析后的数据")
    frame_schema_id: Optional[str] = Field(None, description="使用的帧格式ID")

    # 处理状态
    processing_status: MessageStatus = Field(default=MessageStatus.PENDING, description="处理状态")
    target_systems: List[str] = Field(default_factory=list, description="目标系统列表")
    routing_rules: List[str] = Field(default_factory=list, description="应用的路由规则")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")

    # 性能指标
    processing_duration_ms: Optional[int] = Field(None, description="处理耗时（毫秒）")


__all__ = [
    "EventBusMessage",
    "UnifiedMessage",
]