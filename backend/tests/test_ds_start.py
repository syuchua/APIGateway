"""
测试数据源启动/停止功能（v2 API）
"""
import pytest

BASE_URL = "/api/v2"


@pytest.mark.asyncio
async def test_data_source_start(async_client, clean_eventbus):
    # 1. 创建数据源（UDP）
    create_payload = {
        "name": "测试启动数据源",
        "description": "测试启动功能",
        "protocol_type": "UDP",
        "connection_config": {
            "listen_address": "127.0.0.1",
            "listen_port": 19999,
            "max_connections": 10,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        },
        "parse_config": {
            "auto_parse": False,
            "frame_schema_id": None,
            "parse_options": {},
        },
        "is_active": True,
    }

    create_resp = await async_client.post(
        f"{BASE_URL}/data-sources",
        json=create_payload,
    )
    assert create_resp.status_code == 201, create_resp.text

    create_data = create_resp.json()
    assert create_data["success"] is True
    data_source = create_data["data"]
    data_source_id = data_source["id"]

    # 2. 启动数据源
    start_resp = await async_client.post(
        f"{BASE_URL}/data-sources/{data_source_id}/start"
    )
    assert start_resp.status_code == 200, start_resp.text
    start_data = start_resp.json()
    assert start_data["success"] is True
    assert start_data["data"]["status"] == "running"

    # 3. 查询状态
    status_resp = await async_client.get(
        f"{BASE_URL}/data-sources/{data_source_id}/status"
    )
    assert status_resp.status_code == 200, status_resp.text
    status_data = status_resp.json()
    assert status_data["success"] is True
    status_payload = status_data["data"]
    assert status_payload["is_running"] is True
    assert status_payload["protocol_type"] == "UDP"

    # 4. 停止数据源
    stop_resp = await async_client.post(
        f"{BASE_URL}/data-sources/{data_source_id}/stop"
    )
    assert stop_resp.status_code == 200, stop_resp.text
    stop_data = stop_resp.json()
    assert stop_data["success"] is True
    assert stop_data["data"]["status"] == "stopped"

    # 5. 删除数据源
    delete_resp = await async_client.delete(
        f"{BASE_URL}/data-sources/{data_source_id}"
    )
    assert delete_resp.status_code == 200, delete_resp.text
    delete_data = delete_resp.json()
    assert delete_data["success"] is True


@pytest.mark.asyncio
async def test_data_source_start_websocket(async_client, clean_eventbus):
    payload = {
        "name": "测试WS数据源",
        "protocol_type": "WEBSOCKET",
        "connection_config": {
            "listen_address": "0.0.0.0",
            "listen_port": 9001,
            "endpoint": "/ws/test",
            "max_connections": 5,
        },
        "is_active": True,
    }

    create_resp = await async_client.post(f"{BASE_URL}/data-sources", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    ds_id = create_resp.json()["data"]["id"]

    start_resp = await async_client.post(f"{BASE_URL}/data-sources/{ds_id}/start")
    assert start_resp.status_code == 200, start_resp.text

    status_resp = await async_client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
    status_payload = status_resp.json()["data"]
    assert status_payload["protocol_type"] == "WEBSOCKET"
    assert status_payload["is_running"] is True

    stop_resp = await async_client.post(f"{BASE_URL}/data-sources/{ds_id}/stop")
    assert stop_resp.json()["data"]["status"] == "stopped"

    await async_client.delete(f"{BASE_URL}/data-sources/{ds_id}")


@pytest.mark.asyncio
async def test_data_source_start_mqtt(async_client, clean_eventbus):
    payload = {
        "name": "测试MQTT数据源",
        "protocol_type": "MQTT",
        "connection_config": {
            "listen_address": "0.0.0.0",
            "listen_port": 1883,
            "broker_host": "localhost",
            "broker_port": 1883,
            "topics": ["gateway/in/#"],
            "client_id": "test-client",
        },
        "is_active": True,
    }

    create_resp = await async_client.post(f"{BASE_URL}/data-sources", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    ds_id = create_resp.json()["data"]["id"]

    start_resp = await async_client.post(f"{BASE_URL}/data-sources/{ds_id}/start")
    assert start_resp.status_code == 200, start_resp.text

    status_resp = await async_client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
    status_payload = status_resp.json()["data"]
    assert status_payload["protocol_type"].upper() == "MQTT"
    assert status_payload["is_running"] is True

    stop_resp = await async_client.post(f"{BASE_URL}/data-sources/{ds_id}/stop")
    assert stop_resp.json()["data"]["status"] == "stopped"

    await async_client.delete(f"{BASE_URL}/data-sources/{ds_id}")
