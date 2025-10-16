"""
快速API测试脚本
"""
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app


async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        # 测试创建数据源
        data = {
            "name": "测试UDP数据源",
            "description": "用于测试的UDP数据源",
            "protocol_type": "udp",
            "listen_address": "0.0.0.0",
            "listen_port": 8001,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        }

        print(f"发送POST请求到: /api/v1/data-sources/")
        response = await client.post("/api/v1/data-sources/", json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 201:
            print("\n[SUCCESS] 创建成功!")
            result = response.json()
            ds_id = result["id"]

            # 测试获取列表
            print(f"\n获取数据源列表...")
            list_resp = await client.get("/api/v1/data-sources/")
            print(f"状态码: {list_resp.status_code}")
            print(f"列表数量: {len(list_resp.json())}")

            # 测试获取详情
            print(f"\n获取数据源详情 {ds_id}...")
            detail_resp = await client.get(f"/api/v1/data-sources/{ds_id}")
            print(f"状态码: {detail_resp.status_code}")
            print(f"详情: {detail_resp.json()}")
        else:
            print(f"\n[FAIL] 创建失败!")


if __name__ == "__main__":
    asyncio.run(test())
