"""
路由规则相关Pydantic Schemas
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import Field, field_validator

from .common import BaseSchema, TimestampMixin, UUIDMixin, ProtocolType


class ConditionOperator(str, Enum):
    """条件运算符"""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"


class LogicalOperator(str, Enum):
    """逻辑运算符"""
    AND = "AND"
    OR = "OR"


class RoutingCondition(BaseSchema):
    """路由条件（内部使用）"""
    field_path: str = Field(..., description="字段路径（例如：parsed_data.temperature）")
    operator: ConditionOperator = Field(..., description="条件运算符")
    value: Any = Field(..., description="比较值")


# === 业务导向的路由规则Schema ===

class ParserConfig(BaseSchema):
    """解析器配置"""
    type: str = Field(default="JSON", description="解析器类型（JSON/XML/FrameSchema等）")
    enabled: bool = Field(default=True, description="是否启用解析")
    options: Optional[Dict[str, Any]] = Field(None, description="解析器选项")


class ValidatorConfig(BaseSchema):
    """验证器配置"""
    enabled: bool = Field(default=True, description="是否启用验证")
    rules: Optional[List[Dict[str, Any]]] = Field(None, description="验证规则")


class TransformerConfig(BaseSchema):
    """转换器配置"""
    enabled: bool = Field(default=False, description="是否启用转换")
    script: Optional[str] = Field(None, description="转换脚本")
    mappings: Optional[Dict[str, str]] = Field(None, description="字段映射")


class PipelineConfig(BaseSchema):
    """处理管道配置"""
    parser: ParserConfig = Field(default_factory=ParserConfig, description="解析器配置")
    validator: ValidatorConfig = Field(default_factory=ValidatorConfig, description="验证器配置")
    transformer: TransformerConfig = Field(default_factory=TransformerConfig, description="转换器配置")


class SourceConfig(BaseSchema):
    """数据源配置"""
    protocols: List[ProtocolType] = Field(default_factory=list, description="接入协议列表")
    pattern: Optional[str] = Field(None, description="数据模式匹配（支持通配符，如user.*）")
    source_ids: Optional[List[UUID]] = Field(None, description="指定数据源ID列表")


class TargetSystemConfig(BaseSchema):
    """目标系统配置"""
    id: UUID = Field(..., description="目标系统ID")
    timeout: Optional[int] = Field(5000, description="转发超时时间（毫秒）")
    retry: Optional[int] = Field(3, description="重试次数")
    protocol_options: Optional[Dict[str, Any]] = Field(None, description="协议特定选项")


class RoutingRuleCreate(BaseSchema):
    """创建路由规则Schema（业务导向）"""
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    priority: int = Field(default=50, ge=1, le=100, description="优先级（1-100，数字越大优先级越高）")

    # 数据源配置
    source_config: SourceConfig = Field(..., description="数据源配置")

    # 处理管道配置
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig, description="处理管道配置")

    # 目标系统配置
    target_systems: List[TargetSystemConfig] = Field(..., min_length=1, description="目标系统配置列表")

    # 发布状态
    is_published: bool = Field(default=False, description="是否发布")

    # 兼容旧版API（内部使用）
    conditions: Optional[List[RoutingCondition]] = Field(None, description="路由条件列表（内部使用）")
    logical_operator: Optional[LogicalOperator] = Field(None, description="逻辑运算符（内部使用）")

    @field_validator('logical_operator', mode='before')
    @classmethod
    def normalize_logical_operator(cls, v):
        """将逻辑运算符转换为大写"""
        if v is not None and isinstance(v, str):
            return v.upper()
        return v


class RoutingRuleUpdate(BaseSchema):
    """更新路由规则Schema（业务导向）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=100)

    # 数据源配置
    source_config: Optional[SourceConfig] = None

    # 处理管道配置
    pipeline: Optional[PipelineConfig] = None

    # 目标系统配置
    target_systems: Optional[List[TargetSystemConfig]] = None

    # 状态
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None

    # 兼容旧版API（内部使用）
    conditions: Optional[List[RoutingCondition]] = None
    logical_operator: Optional[LogicalOperator] = None

    @field_validator('logical_operator', mode='before')
    @classmethod
    def normalize_logical_operator(cls, v):
        """将逻辑运算符转换为大写"""
        if v is not None and isinstance(v, str):
            return v.upper()
        return v


class RoutingRuleResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """路由规则响应Schema（业务导向）"""
    name: str
    description: Optional[str] = None
    priority: int

    # 数据源配置
    source_config: SourceConfig

    # 处理管道配置
    pipeline: PipelineConfig

    # 目标系统配置
    target_systems: List[TargetSystemConfig]
    target_system_ids: List[UUID] = Field(default_factory=list, description="目标系统ID列表")

    # 状态
    is_active: bool
    is_published: bool

    # 统计信息
    match_count: Optional[int] = Field(0, description="匹配次数")
    last_match_at: Optional[str] = Field(None, description="最后匹配时间")

    # 兼容旧版API（内部使用）
    conditions: Optional[List[RoutingCondition]] = None
    logical_operator: Optional[LogicalOperator] = None


__all__ = [
    "ConditionOperator",
    "LogicalOperator",
    "RoutingCondition",
    "ParserConfig",
    "ValidatorConfig",
    "TransformerConfig",
    "PipelineConfig",
    "SourceConfig",
    "TargetSystemConfig",
    "RoutingRuleCreate",
    "RoutingRuleUpdate",
    "RoutingRuleResponse",
]
