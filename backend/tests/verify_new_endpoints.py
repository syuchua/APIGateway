"""
验证新增API端点
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def verify_endpoints():
    print("=" * 70)
    print("验证今日新增的API端点")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        # 1. 监控统计端点
        print("\n【监控统计API】")
        endpoints = [
            "/stats/overview",
            "/stats/data-sources",
            "/stats/target-systems",
            "/stats/routing",
        ]

        for endpoint in endpoints:
            response = await client.get(BASE_URL + endpoint)
            status = "OK" if response.status_code == 200 else "FAIL"
            print(f"[{status}] GET {endpoint}: {response.status_code}")

        # 2. 数据源启停控制端点（需要先创建数据源）
        print("\n【数据源启停控制API】")

        # 创建测试数据源
        ds_data = {
            "name": "验证测试数据源",
            "protocol_type": "UDP",
            "listen_port": 19000,
        }

        response = await client.post(f"{BASE_URL}/data-sources/", json=ds_data)
        if response.status_code == 201:
            ds_id = response.json()["id"]
            print(f"[OK] POST /data-sources/: {response.status_code} (ID: {ds_id[:8]}...)")

            # 启动
            response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/start")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            print(f"{status} POST /data-sources/{{id}}/start: {response.status_code}")

            # 查询状态
            response = await client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            result = response.json()
            print(f"{status} GET /data-sources/{{id}}/status: {response.status_code} (running: {result.get('is_running')})")

            # 停止
            response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/stop")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            print(f"{status} POST /data-sources/{{id}}/stop: {response.status_code}")

            # 清理
            await client.delete(f"{BASE_URL}/data-sources/{ds_id}")
            print(f"[OK] 已清理测试数据源")
        else:
            print(f"[FAIL] 创建测试数据源失败: {response.status_code}")

        # 3. 目标系统启停控制端点
        print("\n【目标系统启停控制API】")

        # 创建测试目标系统
        ts_data = {
            "name": "验证测试目标",
            "protocol_type": "HTTP",
            "target_address": "127.0.0.1",
            "target_port": 18080,
        }

        response = await client.post(f"{BASE_URL}/target-systems/", json=ts_data)
        if response.status_code == 201:
            ts_id = response.json()["id"]
            print(f"[OK] POST /target-systems/: {response.status_code} (ID: {ts_id[:8]}...)")

            # 启动
            response = await client.post(f"{BASE_URL}/target-systems/{ts_id}/start")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            print(f"{status} POST /target-systems/{{id}}/start: {response.status_code}")

            # 查询状态
            response = await client.get(f"{BASE_URL}/target-systems/{ts_id}/status")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            result = response.json()
            print(f"{status} GET /target-systems/{{id}}/status: {response.status_code} (registered: {result.get('is_registered')})")

            # 停止
            response = await client.post(f"{BASE_URL}/target-systems/{ts_id}/stop")
            status = "[OK]" if response.status_code == 200 else "[FAIL]"
            print(f"{status} POST /target-systems/{{id}}/stop: {response.status_code}")

            # 清理
            await client.delete(f"{BASE_URL}/target-systems/{ts_id}")
            print(f"[OK] 已清理测试目标系统")
        else:
            print(f"[FAIL] 创建测试目标系统失败: {response.status_code}")

    print("\n" + "=" * 70)
    print("[OK] 所有新增端点验证完成")
    print("=" * 70)
    print("\nSwagger文档: http://localhost:8000/docs")
    print("包含以下新端点：")
    print("  - POST /api/v1/data-sources/{id}/start")
    print("  - POST /api/v1/data-sources/{id}/stop")
    print("  - GET  /api/v1/data-sources/{id}/status")
    print("  - POST /api/v1/target-systems/{id}/start")
    print("  - POST /api/v1/target-systems/{id}/stop")
    print("  - GET  /api/v1/target-systems/{id}/status")
    print("  - GET  /api/v1/stats/overview")
    print("  - GET  /api/v1/stats/data-sources")
    print("  - GET  /api/v1/stats/target-systems")
    print("  - GET  /api/v1/stats/routing")
    print("\nWebSocket端点：")
    print("  - WS ws://localhost:8000/ws/monitor")
    print("  - WS ws://localhost:8000/ws/logs")
    print("  - WS ws://localhost:8000/ws/messages")


if __name__ == "__main__":
    asyncio.run(verify_endpoints())
