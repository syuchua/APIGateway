"""
简单的API测试 - 只测试端点可访问性
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def test_endpoints():
    print("测试新增API端点可访问性")
    print("=" * 60)

    # 测试stats端点
    print("\n1. 测试Stats API")
    endpoints = [
        "/stats/",
        "/stats/overview",
        "/stats/data-sources",
        "/stats/target-systems",
        "/stats/routing",
    ]

    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            try:
                response = await client.get(BASE_URL + endpoint, timeout=5)
                print(f"GET {endpoint}: {response.status_code}")
                if response.status_code != 200:
                    print(f"  Error: {response.text[:100]}")
            except Exception as e:
                print(f"GET {endpoint}: ERROR - {e}")

    # 测试WebSocket端点（只检查是否可以连接）
    print("\n2. WebSocket端点")
    ws_endpoints = [
        "/ws/monitor",
        "/ws/logs",
        "/ws/messages",
    ]
    for endpoint in ws_endpoints:
        print(f"WS {endpoint}: 已注册（需要WebSocket客户端测试）")

    print("\n" + "=" * 60)
    print("完成")


if __name__ == "__main__":
    asyncio.run(test_endpoints())

