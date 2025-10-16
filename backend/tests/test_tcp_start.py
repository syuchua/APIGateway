"""
测试TCP数据源启动
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_tcp_start():
    async with httpx.AsyncClient() as client:
        # 1. 创建TCP数据源
        ds_data = {
            "name": "测试TCP数据源",
            "description": "测试TCP协议启动",
            "protocol_type": "TCP",
            "listen_address": "127.0.0.1",
            "listen_port": 19998,
            "max_connections": 50,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        }

        print("1. 创建TCP数据源...")
        response = await client.post(f"{BASE_URL}/data-sources/", json=ds_data)
        print(f"   状态码: {response.status_code}")

        if response.status_code != 201:
            print(f"   错误: {response.text}")
            return

        ds = response.json()
        ds_id = ds["id"]
        print(f"   成功，ID: {ds_id}")

        # 2. 启动TCP数据源
        print("\n2. 启动TCP数据源...")
        response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/start")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   消息: {result.get('message')}")
        else:
            print(f"   错误: {response.text[:300]}")

        # 3. 查询状态
        print("\n3. 查询运行状态...")
        response = await client.get(f"{BASE_URL}/data-sources/{ds_id}/status")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            status = response.json()
            print(f"   运行中: {status.get('is_running')}")
            if status.get('stats'):
                print(f"   监听端口: {status['stats'].get('listen_port')}")
                print(f"   连接数: {status['stats'].get('connections')}")

        # 4. 停止
        print("\n4. 停止数据源...")
        response = await client.post(f"{BASE_URL}/data-sources/{ds_id}/stop")
        print(f"   状态码: {response.status_code}")

        # 5. 清理
        print("\n5. 清理测试数据...")
        await client.delete(f"{BASE_URL}/data-sources/{ds_id}")
        print("   完成")

if __name__ == "__main__":
    asyncio.run(test_tcp_start())
