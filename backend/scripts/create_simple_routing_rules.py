#!/usr/bin/env python3
"""
测试脚本：创建标准化的测试路由规则（基于 v2 API）。

使用方法：
    cd backend
    uv run python scripts/create_simple_routing_rules.py

脚本假定已经运行：
    uv run python scripts/create_test_data_sources.py
    uv run python scripts/create_test_target_systems.py

作用：
1. 读取现有数据源 / 目标系统。
2. 将常用组合（UDP/HTTP/MQTT/WS/TCP）与本地目标系统关联。
3. 创建一组已发布的路由规则，便于端到端集成测试。
"""

from __future__ import annotations

import sys
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx  # noqa: E402


BASE_URL = os.getenv("GATEWAY_API_BASE_URL", "http://localhost:8000")
AUTH_USERNAME = os.getenv("GATEWAY_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("GATEWAY_PASSWORD", "admin123")


async def authenticate(client: httpx.AsyncClient) -> Optional[str]:
    """登录并返回 access_token"""
    payload = {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}
    try:
        response = await client.post(f"{BASE_URL}/api/v1/auth/login", json=payload)
    except httpx.HTTPError as exc:
        print(f"❌ 无法访问认证接口: {exc}")
        return None

    if response.status_code != 200:
        print(f"❌ 登录失败 ({response.status_code}): {response.text}")
        return None

    data = response.json()
    token = data.get("access_token")
    if not token:
        print("❌ 认证接口返回异常，缺少 access_token")
        return None

    client.headers.update({"Authorization": f"Bearer {token}"})
    print(f"🔑 已使用账号 '{AUTH_USERNAME}' 完成认证")
    return token


async def fetch_items(client: httpx.AsyncClient, endpoint: str) -> List[Dict]:
    """通用分页列表获取函数"""
    response = await client.get(f"{BASE_URL}{endpoint}")
    if response.status_code != 200:
        print(f"❌ 获取 {endpoint} 失败: {response.status_code} {response.text[:120]}")
        return []
    try:
        payload = response.json()
    except ValueError:
        print(f"❌ {endpoint} 返回非 JSON 响应: {response.text[:120]}")
        return []
    if not payload.get("success"):
        print(f"❌ {endpoint} 调用未成功: {payload.get('message', '未知错误')}")
        return []
    items = payload.get("items") or payload.get("data") or []
    if not isinstance(items, list):
        print(f"❌ {endpoint} 返回内容格式异常")
        return []
    return items


async def create_routing_rule(client: httpx.AsyncClient, data: Dict) -> Optional[Dict]:
    """调用 API 创建路由规则"""
    response = await client.post(f"{BASE_URL}/api/v2/routing-rules/", json=data)
    if response.status_code in (200, 201):
        payload = response.json()
        if payload.get("success"):
            rule = payload["data"]
            print(f"✅ 创建路由规则: {rule['name']} (优先级 {rule['priority']})")
            return rule
        print(f"❌ 创建路由规则失败: {payload.get('message', '未知错误')}")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:180]}")
    return None


def ensure(mapping: Dict[str, Dict], names: List[str], label: str) -> Optional[List[Dict]]:
    """检查必需的资源是否存在"""
    missing = [name for name in names if name not in mapping]
    if missing:
        print(f"⚠️ 缺少{label} {', '.join(missing)}，跳过相关路由规则")
        return None
    return [mapping[name] for name in names]


async def main() -> None:
    print("\n" + "=" * 80)
    print("创建路由规则测试数据")
    print("=" * 80)

    async with httpx.AsyncClient(
        trust_env=False,
        timeout=15.0,
        follow_redirects=True,
        headers={"Content-Type": "application/json"},
    ) as client:
        token = await authenticate(client)
        if not token:
            print("⚠️ 认证失败，无法创建路由规则。请检查 GATEWAY_USERNAME / GATEWAY_PASSWORD 配置。")
            return

        print("\n📝 获取已有数据源 / 目标系统...")
        data_sources = await fetch_items(client, "/api/v2/data-sources")
        target_systems = await fetch_items(client, "/api/v2/target-systems")

        if not data_sources:
            print("❌ 未找到数据源，请先运行 create_test_data_sources.py")
            return
        if not target_systems:
            print("❌ 未找到目标系统，请先运行 create_test_target_systems.py")
            return

        ds_map = {item["name"]: item for item in data_sources}
        ts_map = {item["name"]: item for item in target_systems}

        print(f"数据源数量: {len(data_sources)} | 目标系统数量: {len(target_systems)}")

        rules_to_create: List[Dict] = []

        # 规则 1: UDP → HTTP 数据仓库
        udp_http_refs = ensure(ds_map, ["UDP 监听数据源"], "数据源")
        http_target_refs = ensure(ts_map, ["HTTP 数据仓库 (无认证)"], "目标系统")
        if udp_http_refs and http_target_refs:
            rules_to_create.append(
                {
                    "name": "UDP→HTTP 全量转发",
                    "description": "UDP 监听数据源统一转发到 HTTP 数据仓库",
                    "source_config": {
                        "protocols": ["UDP"],
                        "source_ids": [udp_http_refs[0]["id"]],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "json", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": http_target_refs[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 90,
                    "is_published": True,
                }
            )

        # 规则 2: HTTP API → 多 HTTP 目标
        http_multi_refs = ensure(
            ds_map,
            ["HTTP API 数据源"],
            "数据源",
        )
        http_targets_multi = ensure(
            ts_map,
            ["HTTP API 服务 (Basic认证)", "云平台 API (Bearer Token)"],
            "目标系统",
        )
        if http_multi_refs and http_targets_multi:
            rules_to_create.append(
                {
                    "name": "HTTP→多目标广播",
                    "description": "HTTP 数据源广播给两个 HTTP 目标系统",
                    "source_config": {
                        "protocols": ["HTTP"],
                        "source_ids": [http_multi_refs[0]["id"]],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "json", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": True, "mappings": {"status": "state"}},
                    },
                    "target_systems": [
                        {"id": http_targets_multi[0]["id"], "timeout": 5000, "retry": 3},
                        {"id": http_targets_multi[1]["id"], "timeout": 5000, "retry": 3},
                    ],
                    "priority": 80,
                    "is_published": True,
                }
            )

        # 规则 3: MQTT → MQTT
        mqtt_refs = ensure(ds_map, ["MQTT 消息队列数据源"], "数据源")
        mqtt_targets = ensure(ts_map, ["MQTT 消息总线"], "目标系统")
        if mqtt_refs and mqtt_targets:
            rules_to_create.append(
                {
                    "name": "MQTT→MQTT 主题转发",
                    "description": "本地 MQTT 数据源转发到 MQTT 目标",
                    "source_config": {
                        "protocols": ["MQTT"],
                        "source_ids": [mqtt_refs[0]["id"]],
                        "pattern": "sensors/#",
                    },
                    "pipeline": {
                        "parser": {"type": "json", "enabled": True, "options": {}},
                        "validator": {"enabled": True, "rules": []},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": mqtt_targets[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 70,
                    "is_published": True,
                }
            )

        # 规则 4: WebSocket → HTTP
        ws_refs = ensure(ds_map, ["WebSocket 实时数据源"], "数据源")
        ws_http_target = ensure(ts_map, ["HTTP 数据仓库 (无认证)"], "目标系统")
        if ws_refs and ws_http_target:
            rules_to_create.append(
                {
                    "name": "WebSocket→HTTP 实时存储",
                    "description": "WebSocket 数据推送到 HTTP 数据仓库",
                    "source_config": {
                        "protocols": ["WEBSOCKET"],
                        "source_ids": [ws_refs[0]["id"]],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "auto", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": ws_http_target[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 60,
                    "is_published": True,
                }
            )

        # 规则 5: TCP → HTTP
        tcp_refs = ensure(ds_map, ["TCP 长连接数据源"], "数据源")
        tcp_target_http = ensure(ts_map, ["HTTP 数据仓库 (无认证)"], "目标系统")
        tcp_target = ensure(ts_map, ["TCP 历史数据库"], "目标系统")
        if tcp_refs and tcp_target_http:
            rules_to_create.append(
                {
                    "name": "TCP→HTTP 工控数据",
                    "description": "TCP 数据源落地到 HTTP 目标",
                    "source_config": {
                        "protocols": ["TCP"],
                        "source_ids": [tcp_refs[0]["id"]],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {
                            "type": "binary",
                            "enabled": True,
                            "options": {"encoding": "utf-8"},
                        },
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": tcp_target_http[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 50,
                    "is_published": True,
                }
            )

        if http_multi_refs and tcp_target:
            rules_to_create.append(
                {
                    "name": "HTTP→TCP 数据中继",
                    "description": "HTTP 数据源同步一份数据到 TCP 历史库",
                    "source_config": {
                        "protocols": ["HTTP"],
                        "source_ids": [http_multi_refs[0]["id"]],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "json", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": tcp_target[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 55,
                    "is_published": True,
                }
            )

        # 规则 6: 多协议聚合 → 企业系统
        agg_target = ensure(ts_map, ["企业系统 (自定义认证)"], "目标系统")
        if agg_target:
            rules_to_create.append(
                {
                    "name": "多协议数据聚合",
                    "description": "UDP/HTTP/MQTT 多协议数据统一聚合后转发",
                    "source_config": {
                        "protocols": ["UDP", "HTTP", "MQTT"],
                        "source_ids": [],  # 所有对应协议
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "auto", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": True, "mappings": {}},
                    },
                    "target_systems": [
                        {"id": agg_target[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 40,
                    "is_published": True,
                }
            )

        # 规则 7: 默认兜底 → HTTP 数据仓库
        if http_target_refs:
            rules_to_create.append(
                {
                    "name": "默认兜底路由",
                    "description": "所有未匹配数据路由到 HTTP 数据仓库",
                    "source_config": {
                        "protocols": [],
                        "source_ids": [],
                        "pattern": "*",
                    },
                    "pipeline": {
                        "parser": {"type": "auto", "enabled": True, "options": {}},
                        "validator": {"enabled": False},
                        "transformer": {"enabled": False},
                    },
                    "target_systems": [
                        {"id": http_target_refs[0]["id"], "timeout": 5000, "retry": 3}
                    ],
                    "priority": 1,
                    "is_published": True,
                }
            )

        if not rules_to_create:
            print("⚠️ 缺少必需的数据源或目标系统，未创建任何路由规则。")
            return

        print("\n" + "=" * 80)
        print("开始创建路由规则...")
        print("=" * 80)

        success_count = 0
        for rule in rules_to_create:
            if await create_routing_rule(client, rule):
                success_count += 1

    print("\n" + "=" * 80)
    print(f"✅ 成功创建 {success_count} 条路由规则")
    print("=" * 80)
    print("\n📊 路由规则列表：")
    for rule in rules_to_create:
        print(f"  • {rule['name']} (优先级 {rule['priority']})")

    print("\n💡 下一步：")
    print("  1. 可通过前端 /routing-rules 页面验证配置。")
    print("  2. 执行 create_test_data_sources.py 后默认会持续发送 'hello world'。")
    print("  3. 若需要模拟目标系统，可在本地端口启动对应服务。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"\n\n❌ 错误: {exc}")
        import traceback

        traceback.print_exc()
