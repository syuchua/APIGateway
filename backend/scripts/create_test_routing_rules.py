#!/usr/bin/env python3
"""
测试脚本：创建全面的测试路由规则

覆盖所有协议类型和各种路由场景：
- UDP, HTTP, MQTT, WebSocket, TCP
- 条件路由、主题路由、多目标路由
- 数据验证、转换、聚合

使用方法：
    cd backend
    uv run python scripts/create_test_routing_rules.py
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


BASE_URL = "http://localhost:8000"


async def get_data_sources(client: httpx.AsyncClient):
    """获取已创建的数据源"""
    response = await client.get(f"{BASE_URL}/api/v2/data-sources/")
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            return result["items"]
    return []


async def get_target_systems(client: httpx.AsyncClient):
    """获取已创建的目标系统"""
    response = await client.get(f"{BASE_URL}/api/v2/target-systems/")
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            return result["items"]
    return []


async def create_routing_rule(client: httpx.AsyncClient, data: dict):
    """创建路由规则"""
    response = await client.post(f"{BASE_URL}/api/v2/routing-rules/", json=data)

    if response.status_code in (200, 201):
        result = response.json()
        if result.get("success"):
            rule = result["data"]
            print(f"✅ 创建路由规则: {rule['name']}")
            print(f"   ID: {rule['id']}, 优先级: {rule['priority']}, 状态: {'启用' if rule['is_active'] else '禁用'}")
            return rule
        else:
            print(f"❌ 创建失败: {result.get('message', '未知错误')}")
    else:
        print(f"❌ HTTP 错误 {response.status_code}: {response.text}")

    return None


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("API 网关路由规则测试数据创建工具")
    print("=" * 70)

    async with httpx.AsyncClient(trust_env=False, timeout=10.0) as client:
        # 获取数据源和目标系统
        print("\n📝 获取已创建的数据源和目标系统...")
        data_sources = await get_data_sources(client)
        target_systems = await get_target_systems(client)

        if not data_sources:
            print("❌ 没有找到数据源，请先运行: uv run python scripts/create_test_data_sources.py")
            return

        if not target_systems:
            print("❌ 没有找到目标系统，请先运行: uv run python scripts/create_test_target_systems.py")
            return

        print(f"✓ 找到 {len(data_sources)} 个数据源")
        print(f"✓ 找到 {len(target_systems)} 个目标系统")

        # 按协议分类数据源
        udp_sources = [ds for ds in data_sources if ds["protocol_type"] == "UDP"]
        http_sources = [ds for ds in data_sources if ds["protocol_type"] == "HTTP"]
        mqtt_sources = [ds for ds in data_sources if ds["protocol_type"] == "MQTT"]
        ws_sources = [ds for ds in data_sources if ds["protocol_type"] == "WEBSOCKET"]
        tcp_sources = [ds for ds in data_sources if ds["protocol_type"] == "TCP"]

        # 按协议分类目标系统
        http_targets = [ts for ts in target_systems if ts["protocol_type"] == "HTTP"]
        ws_targets = [ts for ts in target_systems if ts["protocol_type"] == "WEBSOCKET"]
        mqtt_targets = [ts for ts in target_systems if ts["protocol_type"] == "MQTT"]
        tcp_targets = [ts for ts in target_systems if ts["protocol_type"] == "TCP"]
        udp_targets = [ts for ts in target_systems if ts["protocol_type"] == "UDP"]

        print(f"\n数据源分布: UDP({len(udp_sources)}), HTTP({len(http_sources)}), MQTT({len(mqtt_sources)}), WS({len(ws_sources)}), TCP({len(tcp_sources)})")
        print(f"目标系统分布: HTTP({len(http_targets)}), WS({len(ws_targets)}), MQTT({len(mqtt_targets)}), TCP({len(tcp_targets)}), UDP({len(udp_targets)})")

        rules_created = 0

        print("\n" + "=" * 70)
        print("开始创建路由规则...")
        print("=" * 70)

        # ============ UDP 路由规则 ============
        if udp_sources:
            print("\n【UDP 路由规则】")

            # 规则1: UDP → HTTP 全量转发
            if http_targets:
                rule1 = {
                    "name": "UDP→HTTP 全量数据转发",
                    "description": "将UDP数据源接收的所有数据转发到HTTP目标系统",
                    "source_config": {
                        "protocols": ["UDP"],
                        "data_source_ids": [udp_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [http_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {"encoding": "utf-8"}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False}
                    },
                    "priority": 100,
                    "is_active": True
                }
                if await create_routing_rule(client, rule1):
                    rules_created += 1

            # 规则2: UDP → WebSocket 条件路由（高温报警）
            if ws_targets:
                rule2 = {
                    "name": "UDP→WebSocket 高温报警",
                    "description": "UDP数据温度超过35度时推送WebSocket报警",
                    "source_config": {
                        "protocols": ["UDP"],
                        "data_source_ids": [udp_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [
                        {"field": "temperature", "operator": "gt", "value": 35.0, "value_type": "number"}
                    ],
                    "target_system_ids": [ws_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {
                            "enabled": True,
                            "rules": [
                                {"field": "temperature", "rule_type": "range", "params": {"min": -50, "max": 100}}
                            ]
                        },
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "alert_level", "value": "CRITICAL"}},
                                {"type": "add_field", "params": {"field": "alert_type", "value": "HIGH_TEMPERATURE"}}
                            ]
                        }
                    },
                    "priority": 200,
                    "is_active": True
                }
                if await create_routing_rule(client, rule2):
                    rules_created += 1

            # 规则3: UDP → MQTT 正常数据上报
            if mqtt_targets:
                rule3 = {
                    "name": "UDP→MQTT 正常数据上报",
                    "description": "UDP温度在20-30度范围内时上报到MQTT云端",
                    "source_config": {
                        "protocols": ["UDP"],
                        "data_source_ids": [],  # 所有UDP源
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [
                        {"field": "temperature", "operator": "gte", "value": 20.0, "value_type": "number"},
                        {"field": "temperature", "operator": "lte", "value": 30.0, "value_type": "number"}
                    ],
                    "target_system_ids": [mqtt_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "auto", "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "data_status", "value": "normal"}}
                            ]
                        }
                    },
                    "priority": 150,
                    "is_active": True
                }
                if await create_routing_rule(client, rule3):
                    rules_created += 1

        # ============ HTTP 路由规则 ============
        if http_sources:
            print("\n【HTTP 路由规则】")

            # 规则4: HTTP → HTTP API转发
            if len(http_targets) >= 2:
                rule4 = {
                    "name": "HTTP→HTTP API链式转发",
                    "description": "将HTTP API接收的数据转发到下游HTTP服务",
                    "source_config": {
                        "protocols": ["HTTP"],
                        "data_source_ids": [http_sources[0]["id"]],
                        "pattern": "/api/*",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [http_targets[1]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {
                            "enabled": True,
                            "rules": [
                                {"field": "device_id", "rule_type": "required", "params": {}}
                            ]
                        },
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "gateway_timestamp", "value": "{{now}}"}}
                            ]
                        }
                    },
                    "priority": 120,
                    "is_active": True
                }
                if await create_routing_rule(client, rule4):
                    rules_created += 1

            # 规则5: HTTP → 多目标广播
            if len(http_targets) >= 2:
                rule5 = {
                    "name": "HTTP→多目标广播",
                    "description": "将关键HTTP数据同时发送到多个目标系统",
                    "source_config": {
                        "protocols": ["HTTP"],
                        "data_source_ids": [],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [
                        {"field": "priority", "operator": "eq", "value": "high", "value_type": "string"}
                    ],
                    "target_system_ids": [http_targets[0]["id"], http_targets[1]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "broadcast", "value": True}}
                            ]
                        }
                    },
                    "priority": 180,
                    "is_active": True
                }
                if await create_routing_rule(client, rule5):
                    rules_created += 1

        # ============ MQTT 路由规则 ============
        if mqtt_sources:
            print("\n【MQTT 路由规则】")

            # 规则6: MQTT → MQTT 主题路由
            if mqtt_targets:
                rule6 = {
                    "name": "MQTT→MQTT 传感器数据转发",
                    "description": "将本地MQTT传感器数据转发到云端MQTT broker",
                    "source_config": {
                        "protocols": ["MQTT"],
                        "data_source_ids": [mqtt_sources[0]["id"]],
                        "pattern": "sensors/+/data",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [mqtt_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {
                            "enabled": True,
                            "rules": [
                                {"field": "sensor_id", "rule_type": "required", "params": {}}
                            ]
                        },
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "gateway_id", "value": "gateway-001"}},
                                {"type": "rename_field", "params": {"old_field": "temp", "new_field": "temperature"}}
                            ]
                        }
                    },
                    "priority": 130,
                    "is_active": True
                }
                if await create_routing_rule(client, rule6):
                    rules_created += 1

            # 规则7: MQTT → HTTP webhook
            if http_targets:
                rule7 = {
                    "name": "MQTT→HTTP 事件webhook",
                    "description": "MQTT事件主题数据通过HTTP webhook通知",
                    "source_config": {
                        "protocols": ["MQTT"],
                        "data_source_ids": [mqtt_sources[0]["id"]],
                        "pattern": "events/#",
                        "filters": {}
                    },
                    "conditions": [
                        {"field": "event_type", "operator": "in", "value": ["alarm", "warning"], "value_type": "string"}
                    ],
                    "target_system_ids": [http_targets[-1]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "notification_type", "value": "webhook"}}
                            ]
                        }
                    },
                    "priority": 160,
                    "is_active": True
                }
                if await create_routing_rule(client, rule7):
                    rules_created += 1

        # ============ WebSocket 路由规则 ============
        if ws_sources:
            print("\n【WebSocket 路由规则】")

            # 规则8: WebSocket → HTTP 实时数据存储
            if http_targets:
                rule8 = {
                    "name": "WebSocket→HTTP 实时数据存储",
                    "description": "WebSocket实时流数据通过HTTP API存储到数据库",
                    "source_config": {
                        "protocols": ["WEBSOCKET"],
                        "data_source_ids": [ws_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [http_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "json", "options": {}},
                        "validator": {
                            "enabled": True,
                            "rules": [
                                {"field": "timestamp", "rule_type": "required", "params": {}}
                            ]
                        },
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "source_type", "value": "websocket_stream"}}
                            ]
                        }
                    },
                    "priority": 110,
                    "is_active": True
                }
                if await create_routing_rule(client, rule8):
                    rules_created += 1

            # 规则9: WebSocket → WebSocket 数据中继
            if ws_targets:
                rule9 = {
                    "name": "WebSocket→WebSocket 数据中继",
                    "description": "WebSocket数据中继转发到另一个WebSocket端点",
                    "source_config": {
                        "protocols": ["WEBSOCKET"],
                        "data_source_ids": [ws_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [
                        {"field": "relay", "operator": "eq", "value": True, "value_type": "boolean"}
                    ],
                    "target_system_ids": [ws_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "auto", "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False}
                    },
                    "priority": 140,
                    "is_active": True
                }
                if await create_routing_rule(client, rule9):
                    rules_created += 1

        # ============ TCP 路由规则 ============
        if tcp_sources:
            print("\n【TCP 路由规则】")

            # 规则10: TCP → HTTP 工控数据上报
            if http_targets:
                rule10 = {
                    "name": "TCP→HTTP 工控数据上报",
                    "description": "TCP长连接工控设备数据上报到HTTP API",
                    "source_config": {
                        "protocols": ["TCP"],
                        "data_source_ids": [tcp_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [http_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "binary", "options": {"encoding": "utf-8"}},
                        "validator": {"enabled": False},
                        "transformer": {
                            "enabled": True,
                            "rules": [
                                {"type": "add_field", "params": {"field": "protocol", "value": "tcp"}},
                                {"type": "add_field", "params": {"field": "device_type", "value": "industrial"}}
                            ]
                        }
                    },
                    "priority": 90,
                    "is_active": True
                }
                if await create_routing_rule(client, rule10):
                    rules_created += 1

            # 规则11: TCP → TCP 数据转发
            if tcp_targets:
                rule11 = {
                    "name": "TCP→TCP 透传转发",
                    "description": "TCP数据透传到下游TCP服务器",
                    "source_config": {
                        "protocols": ["TCP"],
                        "data_source_ids": [tcp_sources[0]["id"]],
                        "pattern": "*",
                        "filters": {}
                    },
                    "conditions": [],
                    "target_system_ids": [tcp_targets[0]["id"]],
                    "pipeline": {
                        "parser": {"type": "raw", "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False}
                    },
                    "priority": 80,
                    "is_active": True
                }
                if await create_routing_rule(client, rule11):
                    rules_created += 1

        # ============ 跨协议聚合路由 ============
        print("\n【跨协议聚合路由】")

        # 规则12: 多协议 → HTTP 数据聚合
        if http_targets and (udp_sources or http_sources or mqtt_sources):
            rule12 = {
                "name": "多协议→HTTP 数据聚合中心",
                "description": "将多种协议的数据统一聚合到HTTP数据中心",
                "source_config": {
                    "protocols": ["UDP", "HTTP", "MQTT"],
                    "data_source_ids": [],  # 所有数据源
                    "pattern": "*",
                    "filters": {}
                },
                "conditions": [
                    {"field": "aggregate", "operator": "eq", "value": True, "value_type": "boolean"}
                ],
                "target_system_ids": [http_targets[0]["id"]],
                "pipeline": {
                    "parser": {"type": "auto", "options": {}},
                    "validator": {
                        "enabled": True,
                        "rules": [
                            {"field": "timestamp", "rule_type": "required", "params": {}}
                        ]
                    },
                    "transformer": {
                        "enabled": True,
                        "rules": [
                            {"type": "add_field", "params": {"field": "aggregated", "value": True}},
                            {"type": "add_field", "params": {"field": "pipeline_version", "value": "v2.0"}}
                        ]
                    }
                },
                "priority": 60,
                "is_active": True
            }
            if await create_routing_rule(client, rule12):
                rules_created += 1

        # ============ 默认兜底路由 ============
        print("\n【默认兜底路由】")

        # 规则13: 默认路由（最低优先级）
        if http_targets:
            rule13 = {
                "name": "默认兜底路由",
                "description": "所有未匹配其他规则的数据都转发到默认目标系统",
                "source_config": {
                    "protocols": [],  # 所有协议
                    "data_source_ids": [],  # 所有数据源
                    "pattern": "*",
                    "filters": {}
                },
                "conditions": [],
                "target_system_ids": [http_targets[-1]["id"]],
                "pipeline": {
                    "parser": {"type": "auto", "options": {}},
                    "validator": {"enabled": False},
                    "transformer": {
                        "enabled": True,
                        "rules": [
                            {"type": "add_field", "params": {"field": "routing_type", "value": "default"}},
                            {"type": "add_field", "params": {"field": "unmatched", "value": True}}
                        ]
                    }
                },
                "priority": 1,  # 最低优先级
                "is_active": True
            }
            if await create_routing_rule(client, rule13):
                rules_created += 1

    print("\n" + "=" * 70)
    print(f"✅ 成功创建 {rules_created} 条路由规则！")
    print("=" * 70)

    print("\n📊 路由规则覆盖范围:")
    print("  • UDP路由: 全量转发、条件路由、高温报警")
    print("  • HTTP路由: API链式转发、多目标广播")
    print("  • MQTT路由: 主题路由、事件webhook")
    print("  • WebSocket路由: 实时存储、数据中继")
    print("  • TCP路由: 工控数据上报、透传转发")
    print("  • 跨协议聚合: 多源数据聚合")
    print("  • 默认兜底: 未匹配数据捕获")

    print("\n💡 下一步操作:")
    print("  1. 访问前端路由规则页面: http://localhost:3001/routing-rules")
    print("  2. 查看和编辑创建的路由规则")
    print("  3. 启动数据源适配器接收数据")
    print("  4. 发送测试数据验证路由规则:")
    print("     uv run python scripts/quick_udp_test.py")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
