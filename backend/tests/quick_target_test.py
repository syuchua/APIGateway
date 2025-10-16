"""
快速测试目标系统API
"""
import asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        # 创建目标系统
        data = {
            "name": "测试HTTP目标",
            "description": "用于测试的HTTP目标系统",
            "protocol_type": "http",
            "target_address": "192.168.1.100",
            "target_port": 9000,
            "endpoint_path": "/api/alert",
            "timeout": 30,
            "retry_count": 3,
            "batch_size": 10,
        }
        
        print("\n测试POST请求: /api/v1/target-systems/")
        response = await client.post("/api/v1/target-systems/", json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 201:
            print("\n[SUCCESS] 创建成功!")
            target_id = response.json()["id"]
            
            # 获取目标系统列表
            print("\n获取目标系统列表...")
            list_resp = await client.get("/api/v1/target-systems/")
            print(f"状态码: {list_resp.status_code}")
            print(f"列表长度: {len(list_resp.json())}")
            
            # 获取目标系统详情
            print(f"\n获取目标系统详情 {target_id}...")
            detail_resp = await client.get(f"/api/v1/target-systems/{target_id}")
            print(f"状态码: {detail_resp.status_code}")
            print(f"详情: {detail_resp.json()}")
        else:
            print(f"\n[ERROR] 创建失败: {response.text}")


if __name__ == "__main__":
    asyncio.run(test())
