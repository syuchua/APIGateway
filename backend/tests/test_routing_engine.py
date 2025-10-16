"""
路由引擎测试用例
采用TDD方法测试路由规则匹配和目标系统选择功能
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.core.gateway.routing.engine import RoutingEngine
from app.core.eventbus import get_eventbus, TopicCategory
from app.schemas.routing_rule import (
    RoutingRuleResponse, RoutingCondition, ConditionOperator, LogicalOperator
)
from app.schemas.common import ProtocolType


class TestRoutingCondition:
    """测试路由条件匹配"""

    def test_simple_equality_condition(self):
        """测试简单相等条件"""
        condition = RoutingCondition(
            field_path="source_protocol",
            operator=ConditionOperator.EQUAL,
            value="UDP"
        )

        # 创建路由引擎实例（用于测试条件匹配）
        from app.core.gateway.routing.engine import RoutingEngine
        engine = RoutingEngine(get_eventbus())

        # 测试数据
        message_data = {
            "source_protocol": "UDP",
            "device_id": 100
        }

        assert engine._evaluate_condition(condition, message_data) is True

        # 不匹配的数据
        message_data2 = {
            "source_protocol": "HTTP",
            "device_id": 100
        }

        assert engine._evaluate_condition(condition, message_data2) is False

    def test_greater_than_condition(self):
        """测试大于条件"""
        condition = RoutingCondition(
            field_path="parsed_data.temperature",
            operator=ConditionOperator.GREATER_THAN,
            value=30.0
        )

        from app.core.gateway.routing.engine import RoutingEngine
        engine = RoutingEngine(get_eventbus())

        # 温度35°C，应该匹配
        message_data = {
            "parsed_data": {
                "temperature": 35.0,
                "humidity": 60.0
            }
        }

        assert engine._evaluate_condition(condition, message_data) is True

        # 温度25°C，不应该匹配
        message_data2 = {
            "parsed_data": {
                "temperature": 25.0,
                "humidity": 60.0
            }
        }

        assert engine._evaluate_condition(condition, message_data2) is False

    def test_in_condition(self):
        """测试IN条件（值在列表中）"""
        condition = RoutingCondition(
            field_path="parsed_data.status",
            operator=ConditionOperator.IN,
            value=[1, 2, 3]
        )

        from app.core.gateway.routing.engine import RoutingEngine
        engine = RoutingEngine(get_eventbus())

        message_data = {
            "parsed_data": {
                "status": 2
            }
        }

        assert engine._evaluate_condition(condition, message_data) is True

        message_data2 = {
            "parsed_data": {
                "status": 5
            }
        }

        assert engine._evaluate_condition(condition, message_data2) is False

    def test_nested_field_path(self):
        """测试嵌套字段路径访问"""
        condition = RoutingCondition(
            field_path="parsed_data.sensor.temperature",
            operator=ConditionOperator.GREATER_THAN,
            value=25.0
        )

        from app.core.gateway.routing.engine import RoutingEngine
        engine = RoutingEngine(get_eventbus())

        message_data = {
            "parsed_data": {
                "sensor": {
                    "temperature": 30.0,
                    "humidity": 60.0
                }
            }
        }

        assert engine._evaluate_condition(condition, message_data) is True


class TestRoutingRule:
    """测试路由规则评估"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def simple_rule(self):
        """创建简单路由规则"""
        target_id = uuid4()
        return RoutingRuleResponse(
            id=uuid4(),
            name="UDP温度监控路由",
            description="UDP协议且温度大于30度",
            priority=10,
            is_active=True,
            conditions=[
                RoutingCondition(
                    field_path="source_protocol",
                    operator=ConditionOperator.EQUAL,
                    value="UDP"
                ),
                RoutingCondition(
                    field_path="parsed_data.temperature",
                    operator=ConditionOperator.GREATER_THAN,
                    value=30.0
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[target_id],
            is_published=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_rule_matches_all_conditions(self, eventbus, simple_rule):
        """测试规则匹配所有条件（AND逻辑）"""
        engine = RoutingEngine(eventbus)

        # 符合所有条件的数据
        message_data = {
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 35.0,
                "humidity": 60.0
            }
        }

        assert engine._evaluate_rule(simple_rule, message_data) is True

        # 只符合部分条件的数据（温度不符合）
        message_data2 = {
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 25.0,
                "humidity": 60.0
            }
        }

        assert engine._evaluate_rule(simple_rule, message_data2) is False

    def test_rule_with_or_logic(self, eventbus):
        """测试OR逻辑规则"""
        target_id = uuid4()
        rule = RoutingRuleResponse(
            id=uuid4(),
            name="多协议路由",
            description="UDP或HTTP协议",
            priority=5,
            is_active=True,
            conditions=[
                RoutingCondition(
                    field_path="source_protocol",
                    operator=ConditionOperator.EQUAL,
                    value="UDP"
                ),
                RoutingCondition(
                    field_path="source_protocol",
                    operator=ConditionOperator.EQUAL,
                    value="HTTP"
                )
            ],
            logical_operator=LogicalOperator.OR,
            target_system_ids=[target_id],
            is_published=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        engine = RoutingEngine(eventbus)

        # UDP协议，应该匹配
        message_data1 = {"source_protocol": "UDP"}
        assert engine._evaluate_rule(rule, message_data1) is True

        # HTTP协议，应该匹配
        message_data2 = {"source_protocol": "HTTP"}
        assert engine._evaluate_rule(rule, message_data2) is True

        # TCP协议，不应该匹配
        message_data3 = {"source_protocol": "TCP"}
        assert engine._evaluate_rule(rule, message_data3) is False

    def test_inactive_rule_not_evaluated(self, eventbus):
        """测试非激活规则不被评估"""
        target_id = uuid4()
        inactive_rule = RoutingRuleResponse(
            id=uuid4(),
            name="非激活规则",
            description="测试",
            priority=1,
            is_active=False,  # 未激活
            conditions=[],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[target_id],
            is_published=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        engine = RoutingEngine(eventbus)
        engine.add_rule(inactive_rule)

        message_data = {"source_protocol": "UDP"}
        matched_rules = engine.find_matching_rules(message_data)

        # 非激活规则不应该被匹配
        assert len(matched_rules) == 0


class TestRoutingEngine:
    """测试路由引擎核心功能"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def routing_rules(self):
        """创建多个路由规则"""
        target1_id = uuid4()
        target2_id = uuid4()

        return [
            # 规则1: 高优先级，温度>35度
            RoutingRuleResponse(
                id=uuid4(),
                name="高温告警",
                description="温度超过35度",
                priority=100,
                is_active=True,
                conditions=[
                    RoutingCondition(
                        field_path="parsed_data.temperature",
                        operator=ConditionOperator.GREATER_THAN,
                        value=35.0
                    )
                ],
                logical_operator=LogicalOperator.AND,
                target_system_ids=[target1_id],
                is_published=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            # 规则2: 低优先级，所有UDP数据
            RoutingRuleResponse(
                id=uuid4(),
                name="UDP数据采集",
                description="所有UDP协议数据",
                priority=10,
                is_active=True,
                conditions=[
                    RoutingCondition(
                        field_path="source_protocol",
                        operator=ConditionOperator.EQUAL,
                        value="UDP"
                    )
                ],
                logical_operator=LogicalOperator.AND,
                target_system_ids=[target2_id],
                is_published=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

    def test_engine_initialization(self, eventbus):
        """测试路由引擎初始化"""
        engine = RoutingEngine(eventbus)

        assert engine.eventbus == eventbus
        assert len(engine.rules) == 0

    def test_add_and_remove_rules(self, eventbus, routing_rules):
        """测试添加和删除规则"""
        engine = RoutingEngine(eventbus)

        # 添加规则
        for rule in routing_rules:
            engine.add_rule(rule)

        assert len(engine.rules) == 2

        # 删除规则
        engine.remove_rule(routing_rules[0].id)
        assert len(engine.rules) == 1

    def test_find_matching_rules(self, eventbus, routing_rules):
        """测试查找匹配的规则"""
        engine = RoutingEngine(eventbus)

        for rule in routing_rules:
            engine.add_rule(rule)

        # 测试数据：温度40度，UDP协议
        message_data = {
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 40.0,
                "humidity": 60.0
            }
        }

        matched_rules = engine.find_matching_rules(message_data)

        # 应该匹配两个规则
        assert len(matched_rules) == 2

        # 验证优先级排序（高优先级在前）
        assert matched_rules[0].priority > matched_rules[1].priority
        assert matched_rules[0].name == "高温告警"

    def test_find_matching_rules_partial_match(self, eventbus, routing_rules):
        """测试部分匹配规则"""
        engine = RoutingEngine(eventbus)

        for rule in routing_rules:
            engine.add_rule(rule)

        # 测试数据：温度25度（不触发高温），UDP协议
        message_data = {
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 25.0,
                "humidity": 60.0
            }
        }

        matched_rules = engine.find_matching_rules(message_data)

        # 应该只匹配一个规则（UDP数据采集）
        assert len(matched_rules) == 1
        assert matched_rules[0].name == "UDP数据采集"

    def test_route_message(self, eventbus, routing_rules):
        """测试路由消息"""
        engine = RoutingEngine(eventbus)

        for rule in routing_rules:
            engine.add_rule(rule)

        # 收集路由结果
        routed_messages = []

        def routing_handler(data, topic, source):
            routed_messages.append(data)

        eventbus.subscribe(TopicCategory.ROUTING_DECIDED, routing_handler)

        # 路由消息
        message_data = {
            "message_id": "test-123",
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 40.0,
                "humidity": 60.0
            }
        }

        engine.route_message(message_data)

        # 验证发布了路由结果
        assert len(routed_messages) == 1

        routed = routed_messages[0]
        assert routed["message_id"] == "test-123"
        assert "matched_rules" in routed
        assert len(routed["matched_rules"]) == 2
        assert "target_system_ids" in routed
        assert len(routed["target_system_ids"]) > 0

    def test_route_message_no_match(self, eventbus, routing_rules):
        """测试没有匹配规则的消息"""
        engine = RoutingEngine(eventbus)

        for rule in routing_rules:
            engine.add_rule(rule)

        routed_messages = []

        def routing_handler(data, topic, source):
            routed_messages.append(data)

        eventbus.subscribe(TopicCategory.ROUTING_DECIDED, routing_handler)

        # HTTP协议数据（没有匹配的规则）
        message_data = {
            "message_id": "test-456",
            "source_protocol": "HTTP",
            "raw_data": b"test"
        }

        engine.route_message(message_data)

        # 即使没有匹配规则，也应该发布路由结果（matched_rules为空）
        assert len(routed_messages) == 1
        routed = routed_messages[0]
        assert routed["message_id"] == "test-456"
        assert len(routed["matched_rules"]) == 0
        assert len(routed["target_system_ids"]) == 0


class TestRoutingEngineIntegration:
    """测试路由引擎与EventBus集成"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.mark.asyncio
    async def test_auto_route_on_data_parsed(self, clean_eventbus, eventbus):
        """测试自动路由已解析的数据"""
        target_id = uuid4()
        rule = RoutingRuleResponse(
            id=uuid4(),
            name="自动路由规则",
            description="所有UDP数据",
            priority=10,
            is_active=True,
            conditions=[
                RoutingCondition(
                    field_path="source_protocol",
                    operator=ConditionOperator.EQUAL,
                    value="UDP"
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[target_id],
            is_published=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        engine = RoutingEngine(eventbus)
        engine.add_rule(rule)

        # 启动自动路由（订阅DATA_PARSED主题）
        engine.start_auto_routing()

        # 收集路由结果
        routed_messages = []

        def routing_handler(data, topic, source):
            routed_messages.append(data)

        eventbus.subscribe(TopicCategory.ROUTING_DECIDED, routing_handler)

        # 模拟发布解析后的数据
        message_data = {
            "message_id": "auto-test-1",
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 25.0
            }
        }

        eventbus.publish(
            topic=TopicCategory.DATA_PARSED,
            data=message_data,
            source="test"
        )

        # 等待异步处理
        import asyncio
        await asyncio.sleep(0.1)

        # 验证自动路由
        assert len(routed_messages) == 1
        assert routed_messages[0]["message_id"] == "auto-test-1"
        assert len(routed_messages[0]["matched_rules"]) == 1

        # 停止自动路由
        engine.stop_auto_routing()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
