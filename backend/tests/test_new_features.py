"""
快速测试今日新增功能
测试数据源/目标系统启停控制、监控统计API
"""
import asyncio
import httpx
from uuid import uuid4


BASE_URL = "http://localhost:8000/api/v1"


async def test_new_features():
    """测试今日新增功能"""
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("测试今日新增功能")
        print("=" * 60)

        # 1. 测试监控统计API
        print("\n1. 测试监控统计API")
        print("-" * 40)

        # 概览统计
        response = await client.get(f"{BASE_URL}/stats/overview")
        print(f"GET /stats/overview: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  网关运行状态: {data['gateway']['is_running']}")
            print(f"  数据源总数: {data['data_sources']['total']}")
            print(f"  目标系统总数: {data['target_systems']['total']}")
            print(f"  路由规则总数: {data['routing_rules']['total']}")

        # 数据源统计
        response = await client.get(f"{BASE_URL}/stats/data-sources")
        print(f"\nGET /stats/data-sources: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  数据源总数: {data['total']}")
            print(f"  运行中: {data['running']}")

        # 目标系统统计
        response = await client.get(f"{BASE_URL}/stats/target-systems")
        print(f"\nGET /stats/target-systems: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  目标系统总数: {data['total']}")
            print(f"  已注册: {data['registered']}")

        # 路由统计
        response = await client.get(f"{BASE_URL}/stats/routing")
        print(f"\nGET /stats/routing: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  路由规则总数: {data['total']}")
            print(f"  已发布: {data['published']}")

        # 2. 测试数据源启停控制
        print("\n\n2. 测试数据源启停控制API")
        print("-" * 40)

        # 创建测试数据源
        ds_data = {
            "name": "测试UDP数据源",
            "description": "用于测试启停控制",
            "protocol_type": "UDP",
            "listen_address": "127.0.0.1",
            "listen_port": 9001,
            "auto_parse": False,
            "max_connections": 10,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        }

        response = await client.post(f"{BASE_URL}/data-sources", json=ds_data)
        print(f"POST /data-sources (创建): {response.status_code}")

        if response.status_code == 201:
            ds = response.json()
            ds_id = ds["id"]
            print(f"  数据源ID: {ds_id}")
            print(f"  数据源名称: {ds['name']}")

            # 启动数据源
            response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/start")
            print(f"\nPOST /data-sources/{ds_id}/start: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  消息: {result['message']}")
                print(f"  状态: {result['status']}")

            # 查询状态
            await asyncio.sleep(0.5)
            response = await client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
            print(f"\nGET /data-sources/{ds_id}/status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"  是否运行: {status['is_running']}")
                print(f"  适配器统计: {status.get('stats')}")

            # 停止数据源
            response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/stop")
            print(f"\nPOST /data-sources/{ds_id}/stop: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  消息: {result['message']}")
                print(f"  状态: {result['status']}")

            # 再次查询状态
            await asyncio.sleep(0.5)
            response = await client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
            print(f"\nGET /data-sources/{ds_id}/status (停止后): {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"  是否运行: {status['is_running']}")

            # 清理：删除测试数据源
            await client.delete(f"{BASE_URL}/data-sources/{ds_id}")
            print(f"\n✓ 已清理测试数据源")

        # 3. 测试目标系统启停控制
        print("\n\n3. 测试目标系统启停控制API")
        print("-" * 40)

        # 创建测试目标系统
        ts_data = {
            "name": "测试目标系统",
            "description": "用于测试启停控制",
            "protocol_type": "HTTP",
            "target_address": "127.0.0.1",
            "target_port": 9002,
            "endpoint_path": "/api/data",
            "timeout": 10,
            "retry_count": 2,
            "batch_size": 1,
        }

        response = await client.post(f"{BASE_URL}/target-systems", json=ts_data)
        print(f"POST /target-systems (创建): {response.status_code}")

        if response.status_code == 201:
            ts = response.json()
            ts_id = ts["id"]
            print(f"  目标系统ID: {ts_id}")
            print(f"  目标系统名称: {ts['name']}")

            # 启动目标系统（注册到转发器）
            response = await client.post(f"{BASE_URL}/target-systems/{ts_id}/start")
            print(f"\nPOST /target-systems/{ts_id}/start: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  消息: {result['message']}")
                print(f"  状态: {result['status']}")

            # 查询状态
            await asyncio.sleep(0.5)
            response = await client.get(f"{BASE_URL}/target-systems/{ts_id}/status")
            print(f"\nGET /target-systems/{ts_id}/status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"  是否注册: {status['is_registered']}")

            # 停止目标系统
            response = await client.post(f"{BASE_URL}/target-systems/{ts_id}/stop")
            print(f"\nPOST /target-systems/{ts_id}/stop: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  消息: {result['message']}")
                print(f"  状态: {result['status']}")

            # 再次查询状态
            await asyncio.sleep(0.5)
            response = await client.get(f"{BASE_URL}/target-systems/{ts_id}/status")
            print(f"\nGET /target-systems/{ts_id}/status (停止后): {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"  是否注册: {status['is_registered']}")

            # 清理：删除测试目标系统
            await client.delete(f"{BASE_URL}/target-systems/{ts_id}")
            print(f"\n✓ 已清理测试目标系统")

        print("\n" + "=" * 60)
        print("✓ 所有新增功能测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_new_features())
