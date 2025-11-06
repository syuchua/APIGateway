#!/usr/bin/env python3
"""
测试脚本：创建多种协议和认证类型的目标系统，并自动启动。

使用方法：
    cd backend
    uv run python scripts/create_test_target_systems.py

脚本会：
1. 调用 API v2 创建 HTTP / UDP / TCP / WebSocket / MQTT 目标系统（本地地址）。
2. 覆盖多种认证方式，便于前端表单与后端验证。
3. 创建完成后自动启动目标系统，方便配合数据源与路由规则调试。
"""

from __future__ import annotations

import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx  # noqa: E402

try:
    import websockets  # type: ignore
except ImportError:  # pragma: no cover - 可选依赖
    websockets = None

try:
    import paho.mqtt.client as mqtt  # type: ignore
except ImportError:  # pragma: no cover
    mqtt = None


BASE_URL = os.getenv("GATEWAY_API_BASE_URL", "http://localhost:8000")
AUTH_USERNAME = os.getenv("GATEWAY_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("GATEWAY_PASSWORD", "admin123")


async def authenticate(client: httpx.AsyncClient) -> Optional[str]:
    """登录获取访问令牌"""
    payload = {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}
    try:
        response = await client.post(f"{BASE_URL}/api/v1/auth/login", json=payload)
    except httpx.HTTPError as exc:  # pragma: no cover - 网络异常日志
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


async def ensure_encryption_key(client: httpx.AsyncClient) -> Optional[str]:
    """确保存在激活的加密密钥，返回密钥名称"""
    try:
        response = await client.get(f"{BASE_URL}/api/v1/encryption-keys/")
        if response.status_code == 200:
            keys = response.json()
            if isinstance(keys, list):
                active = next((k for k in keys if k.get("is_active")), None)
                if active:
                    print(f"🔐 已检测到激活密钥: {active['name']}")
                    return active.get("name")
        payload = {
            "name": f"demo-key-{asyncio.get_running_loop().time():.0f}",
            "description": "自动生成的测试密钥",
            "is_active": True,
        }
        resp = await client.post(f"{BASE_URL}/api/v1/encryption-keys/", json=payload)
        if resp.status_code in (200, 201):
            key = resp.json()
            print(f"🔐 已创建并激活测试密钥: {key.get('name')}")
            return key.get("name")
        print(f"⚠️ 创建测试密钥失败: {resp.text}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"⚠️ 检查加密密钥时出错: {exc}")
    return None


# ========== 目标系统模拟器（下游接收端）==========


async def start_http_sink(name: str, port: int):
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            request_head = await reader.readuntil(b"\r\n\r\n")
        except asyncio.IncompleteReadError as exc:  # pragma: no cover - 非预期断开
            request_head = exc.partial

        headers_text = request_head.decode("utf-8", errors="ignore")
        content_length = 0
        for line in headers_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = 0
                break

        body = b""
        if content_length > 0:
            body = await reader.readexactly(content_length)

        body_preview = body.decode("utf-8", errors="ignore") if body else ""
        print(f"📥 HTTP[{name}] 收到请求: {body_preview}")

        response_body = json.dumps({"status": "received", "target": name}).encode("utf-8")
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8") + response_body

        writer.write(response)
        try:
            await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # pragma: no cover
                pass

    try:
        server = await asyncio.start_server(handle, "127.0.0.1", port)
    except OSError as exc:
        print(f"⚠️ HTTP 目标模拟器 '{name}' 无法监听 127.0.0.1:{port}: {exc}")
        return None

    print(f"🛬 HTTP 目标模拟器 '{name}' 监听 127.0.0.1:{port}")
    return server


async def start_tcp_sink(name: str, port: int):
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                preview = data.decode("utf-8", errors="ignore").rstrip()
                if preview:
                    print(f"🔄 TCP[{name}] 收到: {preview}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # pragma: no cover
                pass
    try:
        server = await asyncio.start_server(handle, "127.0.0.1", port)
    except OSError as exc:
        print(f"⚠️ TCP 目标模拟器 '{name}' 无法监听 127.0.0.1:{port}: {exc}")
        return None

    print(f"🛬 TCP 目标模拟器 '{name}' 监听 127.0.0.1:{port}")
    return server


async def start_udp_sink(name: str, port: int):
    loop = asyncio.get_running_loop()

    class UDPSinkProtocol(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, addr):  # type: ignore[override]
            preview = data.decode("utf-8", errors="ignore")
            print(f"📡 UDP[{name}] 来自 {addr}: {preview}")

    try:
        transport, protocol = await loop.create_datagram_endpoint(
            UDPSinkProtocol,
            local_addr=("127.0.0.1", port),
        )
    except OSError as exc:
        print(f"⚠️ UDP 目标模拟器 '{name}' 无法监听 127.0.0.1:{port}: {exc}")
        return None

    print(f"🛬 UDP 目标模拟器 '{name}' 监听 127.0.0.1:{port}")
    return transport, protocol


async def start_websocket_sink(name: str, port: int):
    if websockets is None:
        print(f"⚠️ 未安装 websockets 库，无法启动 WebSocket 目标 '{name}'。执行 `pip install websockets` 可启用。")
        return None

    async def handler(ws, path):  # type: ignore[no-untyped-def]
        print(f"🔌 WebSocket[{name}] 客户端连接: {path}")
        try:
            async for message in ws:
                preview = message if isinstance(message, str) else str(message)
                print(f"🛰️  WebSocket[{name}] 收到: {preview}")
        except websockets.ConnectionClosed:  # type: ignore[attr-defined]
            pass

    try:
        server = await websockets.serve(handler, "127.0.0.1", port)  # type: ignore[attr-defined]
    except OSError as exc:
        print(f"⚠️ WebSocket 目标模拟器 '{name}' 无法监听 127.0.0.1:{port}: {exc}")
        return None

    print(f"🛬 WebSocket 目标模拟器 '{name}' 监听 ws://127.0.0.1:{port}")
    return server


def start_mqtt_sink(name: str, host: str, port: int, topics: List[str]):
    if mqtt is None:
        print(f"⚠️ 未安装 paho-mqtt 库，无法订阅 MQTT 目标 '{name}'。执行 `pip install paho-mqtt` 可启用。")
        return None

    client_kwargs: Dict[str, Any] = {}
    if hasattr(mqtt, "CallbackAPIVersion"):
        client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2
    client = mqtt.Client(**client_kwargs)

    def on_connect(_client, _userdata, _flags, rc, properties=None):  # type: ignore[no-untyped-def]
        if rc == 0:
            print(f"✅ MQTT[{name}] 订阅模拟器已连接 {host}:{port}")
            for topic in topics:
                _client.subscribe(topic)
                print(f"📨 MQTT[{name}] 监听主题: {topic}")
        else:
            print(f"⚠️ MQTT[{name}] 连接失败，返回码: {rc}")

    def on_message(_client, _userdata, msg):  # type: ignore[no-untyped-def]
        payload = msg.payload.decode("utf-8", errors="ignore")
        print(f"📥 MQTT[{name}] {msg.topic}: {payload}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port, keepalive=60)
        client.loop_start()
        return client
    except Exception as exc:  # pylint: disable=broad-except
        print(f"⚠️ MQTT[{name}] 无法连接 {host}:{port}: {exc}")
        return None


async def start_target_sinks() -> Dict[str, Any]:
    sinks: Dict[str, Any] = {}

    http_endpoints = [
        ("HTTP 数据仓库 (无认证)", 9000),
        ("SOA 系统 (HTTP)", 9005),
        ("HTTP API 服务 (Basic认证)", 9001),
        ("云平台 API (Bearer Token)", 9002),
        ("分析服务 (API Key)", 9003),
        ("企业系统 (自定义认证)", 9004),
    ]

    http_servers = []
    for name, port in http_endpoints:
        server = await start_http_sink(name, port)
        if server:
            http_servers.append(server)
    sinks["http"] = http_servers

    udp_endpoint = await start_udp_sink("UDP SCADA 系统", 9101)
    sinks["udp"] = udp_endpoint

    sinks["tcp"] = await start_tcp_sink("TCP 历史数据库", 9201)

    sinks["websocket"] = await start_websocket_sink("WebSocket 实时看板", 9301)

    return sinks


async def stop_target_sinks(sinks: Dict[str, Any]):
    for server in sinks.get("http", []):
        if server is None:
            continue
        server.close()
        try:
            await server.wait_closed()
        except Exception:  # pragma: no cover - 清理
            pass

    udp = sinks.get("udp")
    if udp:
        if isinstance(udp, tuple) and udp:
            transport, _protocol = udp
            if transport:
                transport.close()

    tcp_server = sinks.get("tcp")
    if tcp_server:
        tcp_server.close()
        try:
            await tcp_server.wait_closed()
        except Exception:  # pragma: no cover
            pass


def _clean_dict(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if data is None:
        return None
    return {key: value for key, value in data.items() if value is not None}


async def fetch_existing_target_systems(client: httpx.AsyncClient) -> Dict[str, Dict[str, Any]]:
    """获取现有目标系统映射"""
    try:
        response = await client.get(f"{BASE_URL}/api/v2/target-systems/", params={"limit": 100})
        if response.status_code != 200:
            print(f"⚠️ 获取目标系统列表失败: {response.status_code} {response.text[:120]}")
            return {}
        payload = response.json()
        if not payload.get("success", True):
            detail = payload.get("detail") or payload.get("error") or payload.get("message")
            print(f"⚠️ 获取目标系统列表未成功: {detail or '未知原因'}")
            return {}
        items = payload.get("items") or payload.get("data") or []
        mapping: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                mapping[item["name"]] = item
        return mapping
    except Exception as exc:  # pylint: disable=broad-except
        print(f"⚠️ 获取目标系统列表时出错: {exc}")
        return {}


async def update_target_system(
    client: httpx.AsyncClient,
    target_id: str,
    definition: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """更新目标系统"""
    payload: Dict[str, Any] = {}

    for key in ("description", "is_active", "name"):
        if definition.get(key) is not None:
            payload[key] = definition[key]

    endpoint_cfg = deepcopy(definition.get("endpoint_config"))
    if endpoint_cfg:
        payload["endpoint_config"] = _clean_dict(endpoint_cfg) or endpoint_cfg

    auth_cfg = deepcopy(definition.get("auth_config"))
    if auth_cfg is not None:
        payload["auth_config"] = _clean_dict(auth_cfg) or {"auth_type": auth_cfg.get("auth_type", "none")}

    forwarder_cfg = deepcopy(definition.get("forwarder_config"))
    if forwarder_cfg:
        payload["forwarder_config"] = _clean_dict(forwarder_cfg) or forwarder_cfg

    transform_rules = deepcopy(definition.get("transform_rules"))
    if transform_rules is not None:
        payload["transform_rules"] = transform_rules

    response = await client.put(f"{BASE_URL}/api/v2/target-systems/{target_id}", json=payload)
    if response.status_code in (200, 201):
        result = response.json()
        if result.get("success"):
            updated = result["data"]
            print(f"♻️ 已更新目标系统: {updated['name']} (ID: {updated['id']})")
            return updated
        detail = result.get("detail") or result.get("error") or result.get("message")
        print(f"❌ 更新目标系统失败: {detail or '未知错误'}")
    else:
        print(f"❌ 更新目标系统 HTTP 错误 {response.status_code}: {response.text}")
    return None


async def ensure_target_system(
    client: httpx.AsyncClient,
    definition: Dict[str, Any],
    existing: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """确保目标系统存在"""
    name = definition["name"]
    if name in existing:
        ts = await update_target_system(client, existing[name]["id"], definition)
        if ts:
            existing[name] = ts
        return ts or existing.get(name)

    target = await create_target_system(client, definition)
    if target:
        existing[name] = target
    return target

    ws_server = sinks.get("websocket")
    if ws_server:
        ws_server.close()
        try:
            await ws_server.wait_closed()
        except Exception:  # pragma: no cover
            pass

    mqtt_client = sinks.get("mqtt")
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:  # pragma: no cover
            pass

async def create_target_system(client: httpx.AsyncClient, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """创建目标系统并返回响应内容"""
    response = await client.post(f"{BASE_URL}/api/v2/target-systems/", json=data)
    if response.status_code in (200, 201):
        result = response.json()
        if result.get("success"):
            ts = result["data"]
            auth_type = ts.get("auth_config", {}).get("auth_type", "none") if ts.get("auth_config") else "none"
            print(f"✅ 成功创建目标系统: {ts['name']} (ID: {ts['id']}, 协议: {ts['protocol_type']}, 认证: {auth_type})")
            return ts
        detail = result.get("detail") or result.get("error") or result.get("message")
        print(f"❌ 创建失败: {detail or '未知错误'}")
    else:
        print(f"❌ HTTP 错误 {response.status_code}: {response.text}")
    return None


async def start_target_system(client: httpx.AsyncClient, target: Dict[str, Any]) -> None:
    """启动目标系统"""
    response = await client.post(f"{BASE_URL}/api/v2/target-systems/{target['id']}/start")
    if response.status_code in (200, 201):
        try:
            payload = response.json()
        except ValueError:
            payload = {"success": False, "message": response.text}
        if payload.get("success", True):
            print(f"🚀 目标系统已启动: {target['name']} ({target['id']})")
        elif (payload.get("error") == "目标系统已运行") or "已在运行" in str(payload.get("detail", "")):
            print(f"ℹ️ 目标系统已在运行: {target['name']} ({target['id']})")
        else:
            print(f"⚠️ 启动目标系统失败 {target['name']}: {payload.get('message', '未知错误')}")
    else:
        print(f"⚠️ 启动目标系统失败 {target['name']}: {response.status_code} {response.text[:120]}")


async def main() -> None:
    """主函数"""
    print("=" * 70)
    print("开始创建测试目标系统...")
    print("=" * 70)

    sinks = await start_target_sinks()
    mqtt_listener = None
    managed_targets: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(trust_env=False, headers={"Content-Type": "application/json"}) as client:
        token = await authenticate(client)
        if not token:
            print("⚠️ 认证失败，无法创建目标系统。请检查 GATEWAY_USERNAME / GATEWAY_PASSWORD 配置。")
            await stop_target_sinks(sinks)
            return

        active_key_name = await ensure_encryption_key(client)
        encryption_config: Dict[str, Any] = {"enabled": bool(active_key_name)}
        if active_key_name:
            encryption_config["metadata"] = {"key_name": active_key_name}

        target_definitions: List[Dict[str, Any]] = [
            {
                "name": "HTTP 数据仓库 (无认证)",
                "description": "本地 HTTP 数据仓库，测试无认证场景",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9000,
                    "endpoint_path": "/warehouse/ingest",
                    "use_ssl": False,
                },
                "auth_config": {"auth_type": "none"},
                "forwarder_config": {
                    "timeout": 20,
                    "retry_count": 3,
                    "batch_size": 100,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "SOA 系统 (HTTP)",
                "description": "SOA 简化HTTP服务，监听本地 9005 端口",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9005,
                    "endpoint_path": "/soa/service",
                    "use_ssl": False,
                },
                "auth_config": {"auth_type": "none"},
                "forwarder_config": {
                    "timeout": 10,
                    "retry_count": 2,
                    "batch_size": 100,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "HTTP API 服务 (Basic认证)",
                "description": "模拟 Basic Auth API，监听本地 9001 端口",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9001,
                    "endpoint_path": "/api/basic/webhook",
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "basic",
                    "username": "gateway_client",
                    "password": "secure_password_123",
                },
                "forwarder_config": {
                    "timeout": 15,
                    "retry_count": 5,
                    "batch_size": 50,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "transform_rules": {
                    "field_mapping": {
                        "timestamp": "event_time",
                        "data": "payload",
                    }
                },
                "is_active": True,
            },
            {
                "name": "云平台 API (Bearer Token)",
                "description": "Bearer Token 场景，监听本地 9002 端口",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9002,
                    "endpoint_path": "/api/bearer/ingest",
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "bearer",
                    "token": "test_bearer_token_example",
                },
                "forwarder_config": {
                    "timeout": 20,
                    "retry_count": 3,
                    "batch_size": 200,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "分析服务 (API Key)",
                "description": "API Key 场景，监听本地 9003 端口",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9003,
                    "endpoint_path": "/analytics/collect",
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "api_key",
                    "api_key": "ak_local_demo_token",
                    "api_key_header": "X-API-Key",
                },
                "forwarder_config": {
                    "timeout": 10,
                    "retry_count": 2,
                    "batch_size": 500,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "企业系统 (自定义认证)",
                "description": "自定义请求头认证，监听本地 9004 端口",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9004,
                    "endpoint_path": "/internal/export",
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "custom",
                    "custom_headers": {
                        "X-Auth-Token": "custom_auth_token_xyz",
                        "X-Client-ID": "gateway_001",
                        "X-Signature": "hmac_signature_here",
                    },
                },
                "forwarder_config": {
                    "timeout": 25,
                    "retry_count": 4,
                    "batch_size": 100,
                    "compression": False,
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "MQTT 消息总线",
                "description": "内部 MQTT 消息通道（本地 1884 端口）",
                "protocol_type": "MQTT",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 1884,
                    "use_ssl": False,
                },
                "auth_config": {"auth_type": "none"},
                "forwarder_config": {
                    "timeout": 10,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "topic": "gateway/integration",
                    "qos": 1,
                    "retain": False,
                    "client_id": "gateway_test_client",
                    "encryption": encryption_config,
                },
                "transform_rules": {
                    "topic_template": "forward/{{ source }}/{{ device_id }}"
                },
                "is_active": True,
            },
            {
                "name": "UDP SCADA 系统",
                "description": "UDP 目标系统（本地 9101 端口）",
                "protocol_type": "UDP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9101,
                    "use_ssl": False,
                },
                "auth_config": {"auth_type": "none"},
                "forwarder_config": {
                    "timeout": 2,
                    "retry_count": 3,
                    "retry_delay": 0.2,
                    "buffer_size": 4096,
                    "encoding": "utf-8",
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "TCP 历史数据库",
                "description": "TCP 目标系统（本地 9201 端口）",
                "protocol_type": "TCP",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9201,
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "basic",
                    "username": "gateway",
                    "password": "historian_pass",
                },
                "forwarder_config": {
                    "timeout": 30,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "buffer_size": 8192,
                    "encoding": "utf-8",
                    "keep_alive": True,
                    "newline": "\\n",
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
            {
                "name": "WebSocket 实时看板",
                "description": "WebSocket 目标系统（本地 9301 端口）",
                "protocol_type": "WEBSOCKET",
                "endpoint_config": {
                    "target_address": "127.0.0.1",
                    "target_port": 9301,
                    "endpoint_path": "/ws/live",
                    "use_ssl": False,
                },
                "auth_config": {
                    "auth_type": "bearer",
                    "token": "ws_bearer_token_example",
                },
                "forwarder_config": {
                    "timeout": 30,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "ping_interval": 20,
                    "ping_timeout": 10,
                    "close_timeout": 10,
                    "headers": {
                        "X-Client-ID": "gateway_ws_client"
                    },
                    "encryption": encryption_config,
                },
                "is_active": True,
            },
        ]

        existing_targets = await fetch_existing_target_systems(client)
        seen_ids: set[str] = set()

        for definition in target_definitions:
            target = await ensure_target_system(client, definition, existing_targets)
            if target and target.get("id") not in seen_ids:
                managed_targets.append(target)
                seen_ids.add(target["id"])

        if managed_targets:
            print("\n🚀 正在启动目标系统...\n")
            for target in managed_targets:
                await start_target_system(client, target)
            await asyncio.sleep(1)

    mqtt_target = next(
        (t for t in managed_targets if str(t.get("protocol_type", "")).upper() == "MQTT"),
        None,
    )
    if mqtt_target:
        topic_candidates = {
            f"gateway/{mqtt_target['id']}",
            f"gateway/source/+",
            f"forward/{mqtt_target['id']}/#",
        }
        mqtt_listener = start_mqtt_sink(
            mqtt_target["name"],
            host="127.0.0.1",
            port=mqtt_target.get("endpoint_config", {}).get("target_port", 1884),
            topics=sorted(t.strip("/") for t in topic_candidates),
        )
        if mqtt_listener is None:
            print("⚠️ 请确保本地 MQTT Broker 运行在 1884 端口 (例如: mosquitto -p 1884)")
        else:
            sinks["mqtt"] = mqtt_listener

    print("=" * 70)
    print("✅ 所有测试目标系统创建完成！")
    print("=" * 70)
    print("\n📊 创建统计:")
    protocol_counts: Dict[str, int] = {}
    for target in managed_targets:
        protocol = str(target.get("protocol_type", "")).upper()
        protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1

    http_count = protocol_counts.get("HTTP", 0)
    mqtt_count = protocol_counts.get("MQTT", 0)
    udp_count = protocol_counts.get("UDP", 0)
    tcp_count = protocol_counts.get("TCP", 0)
    ws_count = protocol_counts.get("WEBSOCKET", 0)

    print(f"  - HTTP 系统: {http_count} 个 (覆盖 Basic/Bearer/API Key/Custom/None)")
    print(f"  - MQTT 系统: {mqtt_count} 个")
    print(f"  - UDP 系统: {udp_count} 个")
    print(f"  - TCP 系统: {tcp_count} 个")
    print(f"  - WebSocket 系统: {ws_count} 个")

    total_created = len(managed_targets)
    total_planned = len(target_definitions)
    print(f"  总计: {total_created} / {total_planned} 个目标系统\n")
    if total_created < total_planned:
        print("⚠️ 部分目标系统未创建成功，请查看上述错误日志重新检查配置。")

    print("提示：可配合 create_test_data_sources.py 与 create_simple_routing_rules.py 进行端到端联调。")

    print("\n🟢 目标系统模拟器正在运行。按 Ctrl+C 结束。\n")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n⚠️ 停止目标系统模拟器...")
    finally:
        await stop_target_sinks(sinks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"\n\n❌ 发生错误: {exc}")
        import traceback

        traceback.print_exc()
