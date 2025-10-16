"""
统一WebSocket消息格式Schema
"""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import Field

from .common import BaseSchema


class WebSocketMessage(BaseSchema):
    """WebSocket消息基类"""
    type: str = Field(..., description="消息类型 (monitor/log/message/control)")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")
    data: Dict[str, Any] = Field(..., description="消息数据")


class MonitorData(BaseSchema):
    """监控数据"""
    gateway_status: str = Field(..., description="网关状态 (running/stopped/error)")
    adapters_running: int = Field(..., description="运行中的适配器数量")
    adapters_total: int = Field(..., description="适配器总数")
    forwarders_active: int = Field(..., description="活跃转发器数量")
    messages_per_second: float = Field(..., description="每秒消息数")
    messages_total: int = Field(..., description="消息总数")
    error_rate: float = Field(..., description="错误率 (0-1)")
    cpu_usage: Optional[float] = Field(None, description="CPU使用率")
    memory_usage: Optional[float] = Field(None, description="内存使用率")


class MonitorMessage(BaseSchema):
    """监控消息"""
    type: Literal["monitor"] = "monitor"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: MonitorData


class LogData(BaseSchema):
    """日志数据"""
    level: str = Field(..., description="日志级别 (DEBUG/INFO/WARNING/ERROR)")
    message: str = Field(..., description="日志消息")
    source: Optional[str] = Field(None, description="日志来源")
    extra: Optional[Dict[str, Any]] = Field(None, description="额外信息")


class LogMessage(BaseSchema):
    """日志消息"""
    type: Literal["log"] = "log"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: LogData


class MessageData(BaseSchema):
    """实时消息数据"""
    message_id: str = Field(..., description="消息ID")
    source_protocol: str = Field(..., description="来源协议")
    source_id: str = Field(..., description="数据源ID")
    data_size: int = Field(..., description="数据大小")
    processing_status: str = Field(..., description="处理状态")
    target_systems: list[str] = Field(default_factory=list, description="目标系统列表")


class DataMessage(BaseSchema):
    """数据消息"""
    type: Literal["message"] = "message"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: MessageData


class ControlData(BaseSchema):
    """控制指令数据"""
    action: str = Field(..., description="控制动作 (start/stop/pause/resume)")
    target: str = Field(..., description="控制目标 (adapter/forwarder/gateway)")
    target_id: Optional[str] = Field(None, description="目标ID")
    params: Optional[Dict[str, Any]] = Field(None, description="控制参数")


class ControlMessage(BaseSchema):
    """控制消息（客户端发送到服务器）"""
    type: Literal["control"] = "control"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: ControlData


class PingMessage(BaseSchema):
    """心跳消息"""
    type: Literal["ping"] = "ping"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)


class PongMessage(BaseSchema):
    """心跳响应"""
    type: Literal["pong"] = "pong"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)


class ErrorData(BaseSchema):
    """错误数据"""
    error: str = Field(..., description="错误信息")
    code: Optional[str] = Field(None, description="错误代码")
    detail: Optional[str] = Field(None, description="错误详情")


class ErrorMessage(BaseSchema):
    """错误消息"""
    type: Literal["error"] = "error"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: ErrorData


# 便捷函数
def create_monitor_message(data: MonitorData) -> dict:
    """创建监控消息"""
    msg = MonitorMessage(data=data)
    return msg.model_dump(mode='json')


def create_log_message(level: str, message: str, source: str = None, extra: dict = None) -> dict:
    """创建日志消息"""
    log_data = LogData(level=level, message=message, source=source, extra=extra)
    msg = LogMessage(data=log_data)
    return msg.model_dump(mode='json')


def create_data_message(message_data: MessageData) -> dict:
    """创建数据消息"""
    msg = DataMessage(data=message_data)
    return msg.model_dump(mode='json')


def create_error_message(error: str, code: str = None, detail: str = None) -> dict:
    """创建错误消息"""
    error_data = ErrorData(error=error, code=code, detail=detail)
    msg = ErrorMessage(data=error_data)
    return msg.model_dump(mode='json')


__all__ = [
    # 消息类型
    "WebSocketMessage",
    "MonitorMessage",
    "LogMessage",
    "DataMessage",
    "ControlMessage",
    "PingMessage",
    "PongMessage",
    "ErrorMessage",

    # 数据类型
    "MonitorData",
    "LogData",
    "MessageData",
    "ControlData",
    "ErrorData",

    # 便捷函数
    "create_monitor_message",
    "create_log_message",
    "create_data_message",
    "create_error_message",
]
