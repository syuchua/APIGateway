"""
监控相关Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field

from .common import BaseSchema


class PerformanceMetrics(BaseSchema):
    """性能指标Schema"""
    timestamp: datetime = Field(default_factory=datetime.now, description="指标时间戳")
    service_name: str = Field(..., description="服务名称")
    instance_id: str = Field(..., description="实例ID")

    # 吞吐量指标
    messages_received: int = Field(default=0, ge=0, description="接收消息数")
    messages_processed: int = Field(default=0, ge=0, description="处理消息数")
    messages_forwarded: int = Field(default=0, ge=0, description="转发消息数")
    messages_failed: int = Field(default=0, ge=0, description="失败消息数")

    # 延迟指标（毫秒）
    avg_processing_time: float = Field(default=0.0, ge=0, description="平均处理时间")
    p50_processing_time: float = Field(default=0.0, ge=0, description="50分位处理时间")
    p95_processing_time: float = Field(default=0.0, ge=0, description="95分位处理时间")
    p99_processing_time: float = Field(default=0.0, ge=0, description="99分位处理时间")

    # 系统资源指标
    cpu_usage_percent: float = Field(default=0.0, ge=0, le=100, description="CPU使用率")
    memory_usage_mb: float = Field(default=0.0, ge=0, description="内存使用量（MB）")
    active_connections: int = Field(default=0, ge=0, description="活跃连接数")
    queue_depth: int = Field(default=0, ge=0, description="队列深度")


class SystemHealth(BaseSchema):
    """系统健康状态Schema"""
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间戳")
    service_name: str = Field(..., description="服务名称")
    is_healthy: bool = Field(..., description="是否健康")

    # 组件状态
    database_status: str = Field(default="UNKNOWN", description="数据库状态")
    redis_status: str = Field(default="UNKNOWN", description="Redis状态")
    eventbus_status: str = Field(default="UNKNOWN", description="EventBus状态")

    # 详细信息
    health_checks: Dict[str, Any] = Field(default_factory=dict, description="健康检查详情")
    error_messages: List[str] = Field(default_factory=list, description="错误信息列表")
    uptime_seconds: int = Field(default=0, ge=0, description="运行时间（秒）")


__all__ = [
    "PerformanceMetrics",
    "SystemHealth",
]