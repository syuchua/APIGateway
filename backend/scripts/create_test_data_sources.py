#!/usr/bin/env python3
"""
测试脚本：创建多种协议的数据源，并持续发送测试流量。

使用方法：
    cd backend
    uv run python scripts/create_test_data_sources.py

脚本会：
1. 调用 API v2 创建 HTTP/UDP/TCP/WebSocket/MQTT 数据源。
2. 启动适配器。
3. 每 10 秒向每个数据源发送一条协议对应的 "hello world" 消息。
"""

from __future__ import annotations

import sys
import asyncio
import json
import socket
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx  # noqa: E402

try:  # noqa: E402
    import paho.mqtt.client as mqtt  # type: ignore
except ImportError:  # pragma: no cover - 运行时提示即可
    mqtt = None

try:  # noqa: E402
    import websockets  # type: ignore
except ImportError:  # pragma: no cover - 运行时提示即可
    websockets = None


BASE_URL = os.getenv("GATEWAY_API_BASE_URL", "http://localhost:8000")
AUTH_USERNAME = os.getenv("GATEWAY_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("GATEWAY_PASSWORD", "admin123")
HELLO_INTERVAL = 10
LOCAL_HOST = "127.0.0.1"
DEFAULT_WS_ENDPOINT = "/ws"


async def authenticate(client: httpx.AsyncClient) -> Optional[str]:
    """登录并返回访问令牌"""
    payload = {"username": AUTH_USERNAME, "password": AUTH_PASSWORD}
    try:
        response = await client.post(f"{BASE_URL}/api/v1/auth/login", json=payload)
    except httpx.HTTPError as exc:  # pragma: no cover - 网络异常
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


async def ensure_encryption_key(client: httpx.AsyncClient) -> None:
    """确保存在一个激活的加密密钥"""
    try:
        response = await client.get(f"{BASE_URL}/api/v1/encryption-keys/")
        if response.status_code == 200:
            keys = response.json()
            if isinstance(keys, list) and any(k.get("is_active") for k in keys):
                active = next(k for k in keys if k.get("is_active"))
                print(f"🔐 已检测到激活密钥: {active['name']}")
                return
        payload = {
            "name": f"demo-key-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "自动生成的测试密钥",
            "is_active": True,
        }
        resp = await client.post(f"{BASE_URL}/api/v1/encryption-keys/", json=payload)
        if resp.status_code in (200, 201):
            key = resp.json()
            print(f"🔐 已创建并激活测试密钥: {key.get('name')}")
        else:
            print(f"⚠️ 创建测试密钥失败: {resp.text}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"⚠️ 检查加密密钥时出错: {exc}")


def _now_iso() -> str:
    return datetime.now().isoformat()


def _resolve_host(address: Optional[str]) -> str:
    if not address or address in {"0.0.0.0", "::", "*"}:
        return LOCAL_HOST
    return address


async def fetch_existing_data_sources(client: httpx.AsyncClient) -> Dict[str, Dict[str, Any]]:
    """获取现有数据源映射"""
    try:
        response = await client.get(f"{BASE_URL}/api/v2/data-sources/", params={"limit": 100})
        if response.status_code != 200:
            print(f"⚠️ 获取数据源列表失败: {response.status_code} {response.text[:120]}")
            return {}
        payload = response.json()
        if not payload.get("success", True):
            detail = payload.get("detail") or payload.get("error") or payload.get("message")
            print(f"⚠️ 获取数据源列表未成功: {detail or '未知原因'}")
            return {}
        items = payload.get("items") or payload.get("data") or []
        mapping: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                mapping[item["name"]] = item
        return mapping
    except Exception as exc:  # pylint: disable=broad-except
        print(f"⚠️ 获取数据源列表时出错: {exc}")
        return {}


def _clean_dict(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if data is None:
        return None
    return {key: value for key, value in data.items() if value is not None}


async def create_data_source(client: httpx.AsyncClient, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """创建数据源并返回响应体"""
    response = await client.post(f"{BASE_URL}/api/v2/data-sources/", json=data)
    if response.status_code in (200, 201):
        result = response.json()
        if result.get("success"):
            ds = result["data"]
            print(f"✅ 成功创建数据源: {ds['name']} (ID: {ds['id']}, 协议: {ds['protocol_type']})")
            return ds
        detail = result.get("detail") or result.get("error") or result.get("message")
        print(f"❌ 创建失败: {detail or '未知错误'}")
    else:
        print(f"❌ HTTP 错误 {response.status_code}: {response.text}")
    return None


async def update_data_source(
    client: httpx.AsyncClient,
    data_source_id: str,
    data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """更新数据源"""
    payload: Dict[str, Any] = {}
    if data.get("description") is not None:
        payload["description"] = data["description"]
    if data.get("is_active") is not None:
        payload["is_active"] = data["is_active"]

    connection_config = deepcopy(data.get("connection_config"))
    if connection_config:
        payload["connection_config"] = connection_config

    parse_config = deepcopy(data.get("parse_config"))
    if parse_config is not None:
        cleaned = _clean_dict(parse_config) or {}
        if "auto_parse" not in cleaned and parse_config.get("auto_parse") is not None:
            cleaned["auto_parse"] = parse_config["auto_parse"]
        payload["parse_config"] = cleaned

    response = await client.put(
        f"{BASE_URL}/api/v2/data-sources/{data_source_id}",
        json=payload,
    )
    if response.status_code in (200, 201):
        result = response.json()
        if result.get("success"):
            updated = result["data"]
            print(f"♻️ 已更新数据源: {updated['name']} (ID: {updated['id']})")
            return updated
        detail = result.get("detail") or result.get("error") or result.get("message")
        print(f"❌ 更新失败: {detail or '未知错误'}")
    else:
        print(f"❌ 更新数据源 HTTP 错误 {response.status_code}: {response.text}")
    return None


async def ensure_data_source(
    client: httpx.AsyncClient,
    data: Dict[str, Any],
    existing: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """确保指定名称的数据源存在，必要时执行更新"""
    name = data["name"]
    if name in existing:
        ds = await update_data_source(client, existing[name]["id"], data)
        if ds:
            existing[name] = ds
        return ds or existing.get(name)

    ds = await create_data_source(client, data)
    if ds:
        existing[name] = ds
    return ds


async def start_data_source(client: httpx.AsyncClient, ds: Dict[str, Any]) -> None:
    """启动指定数据源"""
    response = await client.post(f"{BASE_URL}/api/v2/data-sources/{ds['id']}/start")
    if response.status_code in (200, 201):
        try:
            result = response.json()
        except ValueError:
            result = {"success": False, "message": response.text}
        if result.get("success", True):
            print(f"🚀 数据源已启动: {ds['name']} ({ds['id']})")
        elif (result.get("error") == "数据源已运行") or "已运行" in str(result.get("detail", "")):
            print(f"ℹ️ 数据源已在运行: {ds['name']} ({ds['id']})")
        else:
            print(f"⚠️ 启动数据源失败 {ds['name']}: {result.get('message', '未知错误')}")
    else:
        print(f"⚠️ 启动数据源失败 {ds['name']}: {response.status_code} {response.text[:120]}")


async def http_hello_task(ds: Dict[str, Any], token: Optional[str]) -> None:
    """每10秒向HTTP数据源注入测试数据"""
    ingest_url = f"{BASE_URL}/api/v2/data-sources/{ds['id']}/ingest"
    print(f"🌐 HTTP[{ds['name']}] 将每 {HELLO_INTERVAL}s POST 到 {ingest_url}")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=5.0, headers=headers, trust_env=False) as client:
        while True:
            payload = {
                "message": "hello world from HTTP",
                "source": ds["name"],
                "timestamp": _now_iso(),
            }
            try:
                response = await client.post(ingest_url, json=payload)
                if response.status_code >= 400:
                    print(f"⚠️ HTTP[{ds['name']}] 响应 {response.status_code}: {response.text[:120]}")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"⚠️ HTTP[{ds['name']}] 发送失败: {exc}")
            await asyncio.sleep(HELLO_INTERVAL)


async def udp_hello_task(ds: Dict[str, Any]) -> None:
    """每10秒向UDP端口发送Hello测试"""
    config = ds.get("connection_config", {})
    port = config.get("listen_port")
    if port is None:
        print(f"⚠️ UDP 数据源 {ds['name']} 缺少 listen_port，跳过测试")
        return

    host = _resolve_host(config.get("listen_address"))
    print(f"📡 UDP[{ds['name']}] 将每 {HELLO_INTERVAL}s 向 {host}:{port} 发送测试报文")
    message_base = {
        "message": "hello world from UDP",
        "source": ds["name"],
    }

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while True:
            payload = message_base | {"timestamp": _now_iso()}
            try:
                sock.sendto(json.dumps(payload).encode("utf-8"), (host, int(port)))
            except Exception as exc:  # pylint: disable=broad-except
                print(f"⚠️ UDP[{ds['name']}] 发送失败: {exc}")
            await asyncio.sleep(HELLO_INTERVAL)


async def tcp_hello_task(ds: Dict[str, Any]) -> None:
    """每10秒向TCP端口发送Hello测试"""
    config = ds.get("connection_config", {})
    port = config.get("listen_port")
    if port is None:
        print(f"⚠️ TCP 数据源 {ds['name']} 缺少 listen_port，跳过测试")
        return

    host = _resolve_host(config.get("listen_address"))
    print(f"🔌 TCP[{ds['name']}] 将每 {HELLO_INTERVAL}s 向 {host}:{port} 写入测试报文")

    while True:
        writer = None
        try:
            reader, writer = await asyncio.open_connection(host, int(port))  # noqa: F841
            print(f"✅ TCP[{ds['name']}] 已连接到 {host}:{port}")
            while True:
                payload = {
                    "message": "hello world from TCP",
                    "source": ds["name"],
                    "timestamp": _now_iso(),
                }
                writer.write(json.dumps(payload).encode("utf-8") + b"\n")
                await writer.drain()
                await asyncio.sleep(HELLO_INTERVAL)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️ TCP[{ds['name']}] 发送失败: {exc}")
            await asyncio.sleep(5)
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()  # type: ignore[func-returns-value]
                except Exception:  # pragma: no cover - 仅用于清理
                    pass


async def websocket_hello_task(ds: Dict[str, Any]) -> None:
    """每10秒向WebSocket监听地址发送Hello测试"""
    if websockets is None:
        print("⚠️ 未安装 websockets 库，跳过 WebSocket 测试。执行 `pip install websockets` 可启用。")
        return

    uri = f"ws://{LOCAL_HOST}:8000/ws/data-sources/{ds['id']}"
    print(f"🛰️  WebSocket[{ds['name']}] 将每 {HELLO_INTERVAL}s 向 {uri} 发送测试消息")

    while True:
        try:
            async with websockets.connect(uri) as ws:  # type: ignore[attr-defined]
                print(f"✅ WebSocket[{ds['name']}] 已连接到 {uri}")
                while True:
                    payload = {
                        "message": "hello world from WebSocket",
                        "source": ds["name"],
                        "timestamp": _now_iso(),
                    }
                    await ws.send(json.dumps(payload))
                    await asyncio.sleep(HELLO_INTERVAL)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️ WebSocket[{ds['name']}] 发送失败: {exc}")
            await asyncio.sleep(5)


async def mqtt_hello_task(ds: Dict[str, Any]) -> None:
    """每10秒向MQTT主题发布Hello测试"""
    if mqtt is None:
        print("⚠️ 未安装 paho-mqtt 库，跳过 MQTT 测试。执行 `pip install paho-mqtt` 可启用。")
        return

    config = ds.get("connection_config", {})
    host = config.get("broker_host") or _resolve_host(config.get("listen_address"))
    port = config.get("broker_port") or config.get("listen_port") or 1883
    topics = config.get("topics") or "gateway/hello"
    username = config.get("username")
    password = config.get("password")

    if isinstance(topics, str):
        topics_list = [t.strip() for t in topics.split(",") if t.strip()]
    else:
        topics_list = list(topics) or ["gateway/hello"]

    loop = asyncio.get_running_loop()

    def _sanitize_topic(raw: str) -> str:
        """将订阅模式转换为可发布的具体主题"""
        topic = raw.strip()
        if not topic:
            return "gateway/demo"
        topic = topic.replace("#", "all")
        if "+" in topic:
            parts = []
            for idx, part in enumerate(topic.split("/")):
                if part == "+":
                    fallback = "demo"
                    if idx == 1:
                        fallback = "sensor"
                    parts.append(fallback)
                else:
                    parts.append(part)
            topic = "/".join(parts)
        return topic

    publish_topics = {_sanitize_topic(topic) for topic in topics_list}
    publish_topics.add(f"gateway/source/{ds['id']}")
    publish_topics = sorted(publish_topics)

    while True:
        client_kwargs: Dict[str, Any] = {}
        if hasattr(mqtt, "CallbackAPIVersion"):
            client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2
        client = mqtt.Client(**client_kwargs)
        if username:
            client.username_pw_set(username, password)

        connected = asyncio.Event()
        connect_success = {"value": False}

        def on_connect(_client, _userdata, _flags, rc, properties=None):  # type: ignore[no-untyped-def]
            if rc == 0:
                connect_success["value"] = True
                print(f"✅ MQTT[{ds['name']}] 已连接到 {host}:{port}")
            else:
                connect_success["value"] = False
                print(f"⚠️ MQTT[{ds['name']}] 连接失败，返回码: {rc}")
            loop.call_soon_threadsafe(connected.set)

        client.on_connect = on_connect  # type: ignore[assignment]
        client.loop_start()
        client.connect_async(host, int(port), keepalive=60)

        try:
            await connected.wait()
            if not connect_success["value"]:
                await asyncio.sleep(5)
                continue

            print(f"📨 MQTT[{ds['name']}] 将每 {HELLO_INTERVAL}s 向 {publish_topics} 发布测试消息")
            while True:
                payload = {
                    "message": "hello world from MQTT",
                    "source": ds["name"],
                    "timestamp": _now_iso(),
                    "data_source_id": ds["id"],
                }
                for topic in publish_topics:
                    result = client.publish(topic, json.dumps(payload), qos=1, retain=False)
                    print(f"🔸 MQTT[{ds['name']}] 发布到 {topic}: {payload}")
                    if result.rc != mqtt.MQTT_ERR_SUCCESS:
                        print(f"⚠️ MQTT[{ds['name']}] 发布到 {topic} 失败，返回码: {result.rc}")
                await asyncio.sleep(HELLO_INTERVAL)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️ MQTT[{ds['name']}] 发送失败: {exc}")
        finally:
            client.loop_stop()
            client.disconnect()
            await asyncio.sleep(5)


async def run_hello_world_senders(data_sources: List[Dict[str, Any]], token: Optional[str]) -> None:
    """启动多协议 Hello World 发送任务"""
    tasks: List[asyncio.Task[None]] = []
    for ds in data_sources:
        protocol = str(ds.get("protocol_type", "")).upper()
        if protocol == "HTTP":
            tasks.append(asyncio.create_task(http_hello_task(ds, token)))
        elif protocol == "UDP":
            tasks.append(asyncio.create_task(udp_hello_task(ds)))
        elif protocol == "TCP":
            tasks.append(asyncio.create_task(tcp_hello_task(ds)))
        elif protocol == "WEBSOCKET":
            tasks.append(asyncio.create_task(websocket_hello_task(ds)))
        elif protocol == "MQTT":
            tasks.append(asyncio.create_task(mqtt_hello_task(ds)))
        else:
            print(f"ℹ️ 暂未实现协议 {protocol} 的自动测试，跳过 {ds['name']}")

    if not tasks:
        print("ℹ️ 未找到需要自动发送 hello world 的数据源")
        return

    print("\n🔁 Hello world 发送任务已启动，按 Ctrl+C 可终止。\n")
    await asyncio.gather(*tasks)


async def main() -> None:
    """主函数"""
    print("=" * 60)
    print("开始创建测试数据源...")
    print("=" * 60)

    managed_sources: List[Dict[str, Any]] = []
    token: Optional[str] = None

    async with httpx.AsyncClient(trust_env=False, headers={"Content-Type": "application/json"}) as client:
        token = await authenticate(client)
        if not token:
            print("⚠️ 认证失败，无法创建数据源。请检查 GATEWAY_USERNAME / GATEWAY_PASSWORD 配置。")
            return

        await ensure_encryption_key(client)
        existing_sources = await fetch_existing_data_sources(client)

        data_source_definitions: List[Dict[str, Any]] = [
            {
                "name": "HTTP API 数据源",
                "description": "用于接收 HTTP API 请求的数据源",
                "protocol_type": "HTTP",
                "connection_config": {
                    "listen_address": "0.0.0.0",
                    "listen_port": 8100,
                    "max_connections": 100,
                    "timeout_seconds": 30,
                    "endpoint": "/ingest",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                },
                "parse_config": {
                    "auto_parse": True,
                    "frame_schema_id": None,
                    "parse_options": {
                        "format": "json",
                        "encoding": "utf-8"
                    }
                },
                "is_active": True
            },
            {
                "name": "UDP 监听数据源",
                "description": "UDP 协议仅监听模式，用于接收工控设备数据",
                "protocol_type": "UDP",
                "connection_config": {
                    "listen_address": "0.0.0.0",
                    "listen_port": 8001,
                    "buffer_size": 2048,
                    "timeout_seconds": 10,
                    "forward_mode": "listen_only"
                },
                "parse_config": {
                    "auto_parse": True,
                    "parse_options": {
                        "format": "binary",
                        "byte_order": "big_endian"
                    }
                },
                "is_active": True
            },
            {
                "name": "UDP 单播转发数据源",
                "description": "UDP 协议单播转发模式",
                "protocol_type": "UDP",
                "connection_config": {
                    "listen_address": "0.0.0.0",
                    "listen_port": 8002,
                    "buffer_size": 1024,
                    "forward_mode": "unicast",
                    "target_hosts": "192.168.1.100:9001,192.168.1.101:9001"
                },
                "parse_config": {
                    "auto_parse": False
                },
                "is_active": True
            },
            {
                "name": "MQTT 消息队列数据源",
                "description": "MQTT 协议数据源，订阅传感器主题",
                "protocol_type": "MQTT",
                "connection_config": {
                    "broker_host": "127.0.0.1",
                    "broker_port": 1883,
                    "listen_port": 1883,
                    "topics": "sensors/+/temperature,sensors/+/humidity",
                    "username": "gateway_user",
                    "password": "gateway_pass",
                    "qos": 1,
                    "timeout_seconds": 60
                },
                "parse_config": {
                    "auto_parse": True,
                    "parse_options": {
                        "format": "json",
                        "validate_schema": True
                    }
                },
                "is_active": True
            },
            {
                "name": "WebSocket 实时数据源",
                "description": "WebSocket 协议，用于实时数据流",
                "protocol_type": "WEBSOCKET",
                "connection_config": {
                    "listen_address": "0.0.0.0",
                    "listen_port": 8003,
                    "max_connections": 50,
                    "endpoint": "/ws",
                    "reconnect_interval": 5,
                    "max_retries": 3
                },
                "parse_config": {
                    "auto_parse": True,
                    "parse_options": {
                        "format": "json"
                    }
                },
                "is_active": True
            },
            {
                "name": "TCP 长连接数据源",
                "description": "TCP 协议，用于持久连接的设备数据",
                "protocol_type": "TCP",
                "connection_config": {
                    "listen_address": "0.0.0.0",
                    "listen_port": 8005,
                    "max_connections": 200,
                    "keep_alive": True,
                    "timeout_seconds": 120
                },
                "parse_config": {
                    "auto_parse": True,
                    "frame_schema_id": None,
                    "parse_options": {
                        "format": "binary",
                        "frame_delimiter": "\\r\\n"
                    }
                },
                "is_active": True
            },
        ]

        managed_sources = []
        seen_ids: set[str] = set()

        for definition in data_source_definitions:
            ds = await ensure_data_source(client, definition, existing_sources)
            if ds and ds.get("id") not in seen_ids:
                managed_sources.append(ds)
                seen_ids.add(ds["id"])

        if managed_sources:
            print("\n🚀 正在启动数据源适配器...\n")
            for ds in managed_sources:
                await start_data_source(client, ds)
            await asyncio.sleep(2)

    print("=" * 60)
    print("✅ 所有测试数据源创建完成！")
    print("=" * 60)

    if managed_sources:
        print("\n🔁 开始自动发送 hello world 测试数据（Ctrl+C 结束）\n")
        try:
            await run_hello_world_senders(managed_sources, token)
        except asyncio.CancelledError:  # pragma: no cover - 终止时忽略
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"\n\n❌ 发生错误: {exc}")
        import traceback

        traceback.print_exc()
