"""
路由引擎实现
根据路由规则评估消息并决定目标系统
"""
import logging
from fnmatch import fnmatch
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.routing_rule import (
    RoutingRuleResponse,
    RoutingCondition,
    ConditionOperator,
    LogicalOperator
)
from app.schemas.common import ProtocolType

logger = logging.getLogger(__name__)


class RoutingEngine:
    """
    路由引擎

    功能：
    - 根据路由规则评估消息
    - 查找匹配的目标系统
    - 支持多种条件运算符
    - 支持AND/OR逻辑
    - 按优先级排序规则
    """

    def __init__(self, eventbus: SimpleEventBus):
        """
        初始化路由引擎

        Args:
            eventbus: EventBus实例
        """
        self.eventbus = eventbus
        self.rules: List[RoutingRuleResponse] = []
        self._auto_routing_active = False
        self._subscription_id = None

    def add_rule(self, rule: RoutingRuleResponse):
        """
        添加路由规则

        Args:
            rule: 路由规则
        """
        self.rules.append(rule)
        # 按优先级排序（优先级高的在前）
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"添加路由规则: {rule.name} (优先级: {rule.priority})")

    def remove_rule(self, rule_id: UUID):
        """
        删除路由规则

        Args:
            rule_id: 规则ID
        """
        self.rules = [r for r in self.rules if r.id != rule_id]
        logger.info(f"删除路由规则: {rule_id}")

    def find_matching_rules(self, message_data: Dict[str, Any]) -> List[RoutingRuleResponse]:
        """
        查找匹配的路由规则

        Args:
            message_data: 消息数据

        Returns:
            匹配的规则列表（按优先级排序）
        """
        matched_rules = []

        for rule in self.rules:
            # 跳过非激活规则
            if not rule.is_active:
                continue

            # 评估规则
            if self._evaluate_rule(rule, message_data):
                matched_rules.append(rule)

        return matched_rules

    def route_message(self, message_data: Dict[str, Any]):
        """
        路由消息到目标系统

        Args:
            message_data: 消息数据
        """
        # 查找匹配的规则
        matched_rules = self.find_matching_rules(message_data)

        # 收集所有目标系统ID（去重）
        target_system_ids = set()
        for rule in matched_rules:
            target_system_ids.update(rule.target_system_ids)

        # 构建路由结果
        routing_result = {
            **message_data,  # 保留原始消息数据
            "matched_rules": [
                {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "priority": rule.priority
                }
                for rule in matched_rules
            ],
            "target_system_ids": [str(tid) for tid in target_system_ids]
        }

        # 发布到ROUTING_DECIDED主题
        self.eventbus.publish(
            topic=TopicCategory.ROUTING_DECIDED,
            data=routing_result,
            source="routing_engine"
        )

        logger.info(
            f"路由消息 {message_data.get('message_id', 'unknown')}: "
            f"{len(matched_rules)} 个规则匹配, {len(target_system_ids)} 个目标系统"
        )

        return routing_result

    def start_auto_routing(self):
        """启动自动路由（订阅DATA_PARSED主题）"""
        if self._auto_routing_active:
            logger.warning("自动路由已经启动")
            return

        def on_data_parsed(data, topic, source):
            """处理解析后的数据"""
            try:
                self.route_message(data)
            except Exception as e:
                logger.error(f"路由消息失败: {e}", exc_info=True)

        self.eventbus.subscribe(TopicCategory.DATA_PARSED, on_data_parsed)
        self._auto_routing_active = True
        logger.info("自动路由已启动")

    def stop_auto_routing(self):
        """停止自动路由"""
        if not self._auto_routing_active:
            return

        # EventBus的unsubscribe功能需要实现
        # 这里暂时只标记状态
        self._auto_routing_active = False
        logger.info("自动路由已停止")

    def _evaluate_rule(self, rule: RoutingRuleResponse, message_data: Dict[str, Any]) -> bool:
        """
        评估单个路由规则

        Args:
            rule: 路由规则
            message_data: 消息数据

        Returns:
            是否匹配
        """
        if not self._matches_source_config(getattr(rule, "source_config", {}), message_data):
            return False

        if not rule.conditions:
            # 没有条件的规则总是匹配
            return True

        # 评估所有条件
        condition_results = [
            self._evaluate_condition(cond, message_data)
            for cond in rule.conditions
        ]

        # 根据逻辑运算符组合结果
        if rule.logical_operator == LogicalOperator.AND:
            return all(condition_results)
        elif rule.logical_operator == LogicalOperator.OR:
            return any(condition_results)
        else:
            logger.warning(f"未知的逻辑运算符: {rule.logical_operator}")
        return False

    def _matches_source_config(self, source_config: Any, message_data: Dict[str, Any]) -> bool:
        """根据source_config中的协议、数据源等信息判断是否匹配"""
        if not source_config:
            return True

        cfg = source_config
        if hasattr(source_config, "model_dump"):
            cfg = source_config.model_dump()

        # 协议匹配
        protocols = cfg.get("protocols") or cfg.get("protocol_types")
        if protocols:
            allowed = []
            for proto in protocols:
                if isinstance(proto, ProtocolType):
                    allowed.append(proto.value.upper())
                else:
                    allowed.append(str(proto).upper())

            msg_proto = message_data.get("source_protocol")
            if isinstance(msg_proto, ProtocolType):
                msg_proto_str = msg_proto.value.upper()
            elif msg_proto:
                msg_proto_str = str(msg_proto).upper()
            else:
                msg_proto_str = ""

            if msg_proto_str not in allowed:
                return False

        # 数据源ID匹配
        source_ids = cfg.get("source_ids") or cfg.get("data_source_ids")
        if source_ids:
            msg_source_id = message_data.get("data_source_id") or message_data.get("source_id")
            if msg_source_id is None:
                return False
            msg_source_id = str(msg_source_id)
            normalized_ids = [str(sid) for sid in source_ids]
            if msg_source_id not in normalized_ids:
                return False

        # 模式匹配
        pattern = cfg.get("pattern") or cfg.get("source_pattern")
        if pattern and pattern not in ("*", None, ""):
            candidate = message_data.get("raw_text")
            if candidate is None:
                parsed = message_data.get("parsed_data")
                if isinstance(parsed, (dict, list)):
                    candidate = str(parsed)
                elif parsed is not None:
                    candidate = str(parsed)
            if candidate is None and message_data.get("raw_data") is not None:
                candidate = str(message_data["raw_data"])

            if candidate is None or not fnmatch(str(candidate), pattern):
                return False

        return True

    def _evaluate_condition(
        self,
        condition: RoutingCondition,
        message_data: Dict[str, Any]
    ) -> bool:
        """
        评估单个条件

        Args:
            condition: 条件
            message_data: 消息数据

        Returns:
            是否满足条件
        """
        # 获取字段值
        field_value = self._get_field_value(message_data, condition.field_path)

        # 如果字段不存在，条件不满足
        if field_value is None:
            return False

        # 根据运算符评估
        operator = condition.operator
        expected_value = condition.value

        try:
            if operator == ConditionOperator.EQUAL:
                return field_value == expected_value

            elif operator == ConditionOperator.NOT_EQUAL:
                return field_value != expected_value

            elif operator == ConditionOperator.GREATER_THAN:
                return field_value > expected_value

            elif operator == ConditionOperator.GREATER_THAN_OR_EQUAL:
                return field_value >= expected_value

            elif operator == ConditionOperator.LESS_THAN:
                return field_value < expected_value

            elif operator == ConditionOperator.LESS_THAN_OR_EQUAL:
                return field_value <= expected_value

            elif operator == ConditionOperator.IN:
                return field_value in expected_value

            elif operator == ConditionOperator.NOT_IN:
                return field_value not in expected_value

            elif operator == ConditionOperator.CONTAINS:
                return expected_value in field_value

            elif operator == ConditionOperator.NOT_CONTAINS:
                return expected_value not in field_value

            else:
                logger.warning(f"未知的条件运算符: {operator}")
                return False

        except Exception as e:
            logger.error(f"评估条件时出错: {e}")
            return False

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        获取嵌套字段的值

        Args:
            data: 数据字典
            field_path: 字段路径（用点分隔，例如 "parsed_data.temperature"）

        Returns:
            字段值，如果不存在返回None
        """
        try:
            parts = field_path.split('.')
            value = data

            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None

                if value is None:
                    return None

            return value

        except Exception as e:
            logger.error(f"获取字段值失败 {field_path}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取路由引擎统计信息"""
        return {
            "total_rules": len(self.rules),
            "active_rules": sum(1 for r in self.rules if r.is_active),
            "auto_routing_active": self._auto_routing_active
        }
