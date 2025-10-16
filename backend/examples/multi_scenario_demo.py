# -*- coding: utf-8 -*-
"""
多协议多场景集成演示 - 纯内存运行版本

演示不同业务场景下的数据接入和转发：
1. IoT传感器数据 (UDP二进制帧)
2. 电商订单数据 (HTTP JSON)
3. 实时聊天消息 (WebSocket JSON)
4. PLC工业数据 (TCP二进制帧)
5. 车联网位置数据 (MQTT JSON)
"""

import asyncio
import sys
import json
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

# 设置Windows控制台UTF-8编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.core.eventbus import SimpleEventBus
from app.core.eventbus.topics import TopicCategory
from app.core.gateway.routing.engine import RoutingEngine

from app.schemas.routing_rule import (
    RoutingRuleResponse,
    RoutingCondition,
    LogicalOperator,
    ConditionOperator
)


class MultiScenarioDemo:
    """多场景集成演示"""

    def __init__(self):
        self.eventbus = SimpleEventBus()
        self.stats = {
            "received": 0,
            "parsed": 0,
            "routed": 0,
            "forwarded": 0
        }
        self.scenarios = []

    async def setup(self):
        """设置环境"""
        self._print_header()
        self._define_scenarios()
        self._setup_routing()
        self._subscribe_events()
        print("\n✅ 环境设置完成\n")

    def _print_header(self):
        """打印标题"""
        print("=" * 100)
        print("API网关多协议多场景集成演示".center(100))
        print("=" * 100)

    def _define_scenarios(self):
        """定义业务场景"""
        print("\n📋 定义业务场景...")

        self.scenarios = [
            {
                "id": 1,
                "name": "IoT传感器监控",
                "protocol": "UDP",
                "description": "温湿度传感器通过UDP发送二进制帧数据",
                "data": {
                    "device_id": 1001,
                    "device_type": "temperature_sensor",
                    "temperature": 25.5,
                    "humidity": 45.0,
                    "battery": 95,
                    "location": "Building A - Room 101"
                }
            },
            {
                "id": 2,
                "name": "电商订单系统",
                "protocol": "HTTP",
                "description": "电商平台通过HTTP POST提交订单数据",
                "data": {
                    "order_id": "ORD20250108001",
                    "order_type": "online_purchase",
                    "user_id": "USER123456",
                    "total_amount": 1299.99,
                    "items_count": 3,
                    "payment_method": "credit_card",
                    "status": "pending"
                }
            },
            {
                "id": 3,
                "name": "实时聊天系统",
                "protocol": "WebSocket",
                "description": "聊天应用通过WebSocket推送实时消息",
                "data": {
                    "message_id": "MSG2025010800001",
                    "message_type": "text",
                    "from_user": "Alice",
                    "to_user": "Bob",
                    "content": "Hello, how are you?",
                    "room_id": "ROOM001",
                    "is_urgent": False
                }
            },
            {
                "id": 4,
                "name": "工业PLC数据采集",
                "protocol": "TCP",
                "description": "PLC设备通过TCP发送工业控制数据",
                "data": {
                    "plc_id": 2001,
                    "plc_type": "modbus",
                    "production_line": "Line-A",
                    "motor_speed": 1500,
                    "temperature": 75.5,
                    "pressure": 2.5,
                    "vibration": 0.05,
                    "alarm_code": 0
                }
            },
            {
                "id": 5,
                "name": "车联网位置跟踪",
                "protocol": "MQTT",
                "description": "车载终端通过MQTT上报位置信息",
                "data": {
                    "vehicle_id": "CAR20250108001",
                    "vehicle_type": "truck",
                    "driver_id": "DRV123",
                    "latitude": 39.9042,
                    "longitude": 116.4074,
                    "speed": 65.5,
                    "direction": 135,
                    "mileage": 125000,
                    "fuel_level": 45
                }
            },
            {
                "id": 6,
                "name": "IoT传感器监控(高温)",
                "protocol": "UDP",
                "description": "温度异常的传感器数据",
                "data": {
                    "device_id": 1002,
                    "device_type": "temperature_sensor",
                    "temperature": 35.0,
                    "humidity": 85.0,
                    "battery": 90,
                    "location": "Building B - Room 201"
                }
            }
        ]

        for scenario in self.scenarios:
            print(f"  ✓ 场景{scenario['id']}: {scenario['name']} ({scenario['protocol']})")

    def _setup_routing(self):
        """设置路由规则"""
        print("\n🔀 设置路由规则...")

        self.routing_engine = RoutingEngine(self.eventbus)

        # 规则1: 传感器温度异常 -> HTTP告警
        rule1 = RoutingRuleResponse(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="传感器温度告警",
            priority=10,
            conditions=[
                RoutingCondition(
                    field_path="temperature",
                    operator=ConditionOperator.GREATER_THAN,
                    value=30.0
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[UUID("22222222-2222-2222-2222-222222222222")],
            is_active=True,
            is_published=True
        )

        # 规则2: 高额订单 -> 实时通知
        rule2 = RoutingRuleResponse(
            id=UUID("11111111-1111-1111-1111-111111111112"),
            name="高额订单通知",
            priority=9,
            conditions=[
                RoutingCondition(
                    field_path="total_amount",
                    operator=ConditionOperator.GREATER_THAN,
                    value=1000.0
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[UUID("22222222-2222-2222-2222-222222222223")],
            is_active=True,
            is_published=True
        )

        # 规则3: PLC报警 -> TCP告警
        rule3 = RoutingRuleResponse(
            id=UUID("11111111-1111-1111-1111-111111111113"),
            name="PLC设备报警",
            priority=10,
            conditions=[
                RoutingCondition(
                    field_path="alarm_code",
                    operator=ConditionOperator.GREATER_THAN,
                    value=0
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[UUID("22222222-2222-2222-2222-222222222224")],
            is_active=True,
            is_published=True
        )

        # 规则4: 车辆超速 -> HTTP违规记录
        rule4 = RoutingRuleResponse(
            id=UUID("11111111-1111-1111-1111-111111111114"),
            name="车辆超速告警",
            priority=9,
            conditions=[
                RoutingCondition(
                    field_path="speed",
                    operator=ConditionOperator.GREATER_THAN,
                    value=60.0
                )
            ],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[UUID("22222222-2222-2222-2222-222222222222")],
            is_active=True,
            is_published=True
        )

        # 规则5: 所有数据 -> 数据湖存储
        rule5 = RoutingRuleResponse(
            id=UUID("11111111-1111-1111-1111-111111111115"),
            name="数据湖存储",
            priority=1,
            conditions=[],
            logical_operator=LogicalOperator.AND,
            target_system_ids=[UUID("22222222-2222-2222-2222-222222222225")],
            is_active=True,
            is_published=True
        )

        for rule in [rule1, rule2, rule3, rule4, rule5]:
            self.routing_engine.add_rule(rule)

        print(f"  ✓ 已加载 5 条路由规则")
        print(f"    - 传感器温度告警 (优先级: 10)")
        print(f"    - 高额订单通知 (优先级: 9)")
        print(f"    - PLC设备报警 (优先级: 10)")
        print(f"    - 车辆超速告警 (优先级: 9)")
        print(f"    - 数据湖存储 (优先级: 1)")

    def _subscribe_events(self):
        """订阅事件"""
        print("\n👂 订阅事件监控...")

        self.eventbus.subscribe(
            TopicCategory.UDP_RECEIVED.value,
            self._on_data_received
        )
        self.eventbus.subscribe(
            TopicCategory.DATA_PARSED.value,
            self._on_data_parsed
        )
        self.eventbus.subscribe(
            TopicCategory.DATA_ROUTED.value,
            self._on_data_routed
        )

        print("  ✓ 事件监控已启动")

    def _on_data_received(self, data: Dict[str, Any], topic: str, source: str):
        """数据接收事件"""
        self.stats["received"] += 1
        protocol = data.get('source_protocol', 'unknown')
        source_id = data.get('source_id', 'unknown')

        print(f"\n📥 [{self.stats['received']}] 接收数据")
        print(f"   ├─ 协议: {protocol}")
        print(f"   └─ 来源: {source_id}")

    def _on_data_parsed(self, data: Dict[str, Any], topic: str, source: str):
        """数据解析事件"""
        self.stats["parsed"] += 1
        parsed = data.get('parsed_data', {})

        print(f"\n📊 [{self.stats['parsed']}] 数据解析完成")

        # 根据数据类型显示关键字段
        if 'device_id' in parsed:
            print(f"   ├─ 设备ID: {parsed.get('device_id')}")
            print(f"   ├─ 温度: {parsed.get('temperature')}℃")
            print(f"   └─ 湿度: {parsed.get('humidity')}%")
        elif 'order_id' in parsed:
            print(f"   ├─ 订单ID: {parsed.get('order_id')}")
            print(f"   ├─ 金额: ¥{parsed.get('total_amount')}")
            print(f"   └─ 状态: {parsed.get('status')}")
        elif 'message_id' in parsed:
            print(f"   ├─ 消息ID: {parsed.get('message_id')}")
            print(f"   ├─ 发送者: {parsed.get('from_user')}")
            print(f"   └─ 内容: {parsed.get('content')}")
        elif 'plc_id' in parsed:
            print(f"   ├─ PLC ID: {parsed.get('plc_id')}")
            print(f"   ├─ 生产线: {parsed.get('production_line')}")
            print(f"   └─ 报警码: {parsed.get('alarm_code')}")
        elif 'vehicle_id' in parsed:
            print(f"   ├─ 车辆ID: {parsed.get('vehicle_id')}")
            print(f"   ├─ 速度: {parsed.get('speed')} km/h")
            print(f"   └─ 位置: ({parsed.get('latitude')}, {parsed.get('longitude')})")

    def _on_data_routed(self, data: Dict[str, Any], topic: str, source: str):
        """数据路由事件"""
        self.stats["routed"] += 1
        targets = data.get('target_systems', [])
        matched_rules = data.get('matched_rules', [])

        print(f"\n🔀 [{self.stats['routed']}] 路由匹配")
        print(f"   ├─ 匹配规则: {len(matched_rules)} 条")
        for rule_name in matched_rules:
            print(f"   │  └─ {rule_name}")
        print(f"   └─ 目标系统: {len(targets)} 个")

    async def simulate_scenarios(self):
        """模拟各场景数据"""
        print("\n" + "=" * 100)
        print("开始模拟多场景数据流".center(100))
        print("=" * 100)

        for scenario in self.scenarios:
            print(f"\n{'='*100}")
            print(f"场景{scenario['id']}: {scenario['name']}".center(100))
            print(f"{scenario['description']}".center(100))
            print(f"{'='*100}")

            # 发布DATA_RECEIVED事件
            self.eventbus.publish(
                TopicCategory.UDP_RECEIVED.value,
                {
                    "message_id": f"MSG-{scenario['id']:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "source_protocol": scenario['protocol'],
                    "source_id": f"{scenario['protocol'].lower()}-adapter-001",
                    "raw_data": json.dumps(scenario['data']).encode('utf-8'),
                }
            )

            await asyncio.sleep(0.3)

            # 发布DATA_PARSED事件
            parsed_data = scenario['data'].copy()
            parsed_data['_scenario'] = scenario['name']
            parsed_data['_protocol'] = scenario['protocol']

            self.eventbus.publish(
                TopicCategory.DATA_PARSED.value,
                {
                    "message_id": f"MSG-{scenario['id']:03d}",
                    "source_id": f"{scenario['protocol'].lower()}-adapter-001",
                    "parsed_data": parsed_data
                }
            )

            await asyncio.sleep(0.5)

        print(f"\n{'='*100}")

    def print_summary(self):
        """打印统计摘要"""
        print("\n" + "=" * 100)
        print("演示完成 - 统计摘要".center(100))
        print("=" * 100)

        print(f"\n📊 数据处理统计:")
        print(f"   ├─ 接收数据: {self.stats['received']} 条")
        print(f"   ├─ 解析数据: {self.stats['parsed']} 条")
        print(f"   └─ 路由匹配: {self.stats['routed']} 次")

        print(f"\n📋 业务场景覆盖:")
        for scenario in self.scenarios:
            print(f"   ✓ {scenario['name']} ({scenario['protocol']})")

        print(f"\n🎯 路由规则演示:")
        print(f"   ✓ 温度>30℃ → 告警系统")
        print(f"   ✓ 订单>1000元 → 实时通知")
        print(f"   ✓ PLC报警 → TCP告警")
        print(f"   ✓ 车速>60km/h → 违规记录")
        print(f"   ✓ 所有数据 → 数据湖存储")

        print("\n" + "=" * 100)


async def main():
    """主函数"""
    demo = MultiScenarioDemo()

    try:
        await demo.setup()
        await asyncio.sleep(0.5)
        await demo.simulate_scenarios()
        await asyncio.sleep(1)
        demo.print_summary()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════════════════════════════════╗
    ║                                                                                                ║
    ║                           API网关多协议多场景集成演示                                          ║
    ║                                                                                                ║
    ║  演示场景:                                                                                     ║
    ║    1. IoT传感器监控     - UDP二进制帧  - 温湿度数据采集                                       ║
    ║    2. 电商订单系统       - HTTP JSON   - 在线订单处理                                         ║
    ║    3. 实时聊天系统       - WebSocket   - 即时消息推送                                         ║
    ║    4. 工业PLC数据采集    - TCP二进制帧 - 工业控制数据                                         ║
    ║    5. 车联网位置跟踪     - MQTT JSON   - 车辆实时定位                                         ║
    ║    6. IoT传感器(高温)    - UDP二进制帧  - 温度异常告警                                        ║
    ║                                                                                                ║
    ║  核心功能:                                                                                     ║
    ║    ✓ 多协议数据接入       ✓ 智能路由规则匹配    ✓ 数据转换处理                               ║
    ║    ✓ 多目标系统转发       ✓ 事件驱动架构        ✓ 实时监控告警                               ║
    ║                                                                                                ║
    ╚════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
