"""
简化的路由规则响应Schema（用于列表展示）
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from pydantic import Field

from .common import BaseSchema, TimestampMixin, UUIDMixin


class RoutingRuleSimpleResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """简化的路由规则响应Schema（用于列表展示，兼容前端旧接口）"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    priority: int = Field(..., description="优先级")

    # 简化的字段
    source_pattern: Optional[str] = Field(None, description="数据源模式（从source_config提取）")
    target_system_ids: List[str] = Field(default_factory=list, description="目标系统ID列表")

    # 状态
    is_active: bool = Field(..., description="是否激活")
    is_published: bool = Field(..., description="是否发布")

    # 统计信息
    match_count: int = Field(default=0, description="匹配次数")
    last_match_at: Optional[datetime] = Field(None, description="最后匹配时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "温度数据路由",
                "description": "将温度数据路由到监控系统",
                "priority": 50,
                "source_pattern": "sensor.*",
                "target_system_ids": ["sys-001", "sys-002"],
                "is_active": True,
                "is_published": True,
                "match_count": 1234,
                "last_match_at": "2025-10-13T10:30:00Z",
                "created_at": "2025-10-01T00:00:00Z",
                "updated_at": "2025-10-13T00:00:00Z"
            }
        }


__all__ = ["RoutingRuleSimpleResponse"]
