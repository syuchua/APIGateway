"""
路由规则ORM模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, UUIDMixin, AuditMixin


class RoutingRule(Base, UUIDMixin, AuditMixin):
    """路由规则模型（业务导向）"""

    __tablename__ = "routing_rules"
    __table_args__ = {"schema": "gateway"}

    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=50, nullable=False)

    # 业务导向字段
    source_config = Column(JSONB, nullable=False, default={})  # 数据源配置
    pipeline = Column(JSONB, nullable=False, default={})  # 处理管道配置
    target_systems = Column(JSONB, nullable=False)  # 目标系统配置列表

    # 兼容旧版字段（内部使用）
    conditions = Column(JSONB, nullable=True, default=[])
    logical_operator = Column(String(10), default="AND", nullable=True)  # AND, OR
    target_system_ids = Column(JSONB, nullable=True)  # 旧版兼容
    data_transformation = Column(JSONB, nullable=True)  # 旧版兼容

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    # 统计信息
    match_count = Column(BigInteger, default=0)
    last_match_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "source_config": self.source_config,
            "pipeline": self.pipeline,
            "target_systems": self.target_systems,
            "conditions": self.conditions,
            "logical_operator": self.logical_operator,
            "target_system_ids": self.target_system_ids,
            "data_transformation": self.data_transformation,
            "is_active": self.is_active,
            "is_published": self.is_published,
            "match_count": self.match_count,
            "last_match_at": self.last_match_at.isoformat() if self.last_match_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    def __repr__(self):
        return f"<RoutingRule(id={self.id}, name={self.name}, priority={self.priority})>"


__all__ = ["RoutingRule"]
