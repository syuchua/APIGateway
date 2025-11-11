#!/usr/bin/env python3
"""
测试脚本：一键创建所有测试数据

使用方法：
    cd backend
    uv run python scripts/create_all_test_data.py
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


BASE_URL = "http://localhost:8000"


async def check_server():
    """检查服务器是否运行"""
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(f"{BASE_URL}/docs", timeout=5.0)
            if response.status_code == 200:
                print("✅ 后端服务器运行正常")
                return True
    except Exception as e:
        print(f"❌ 无法连接到后端服务器: {e}")
        print(f"   请确保后端服务正在运行: http://localhost:8000")
        return False


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("API 网关测试数据创建工具")
    print("=" * 60)

    # 检查服务器
    if not await check_server():
        return

    print("\n📝 将创建以下测试数据:")
    print("  - 6 个数据源 (HTTP, UDP×2, MQTT, WebSocket, TCP)")
    print("  - 10 个目标系统 (覆盖所有协议和认证类型)")
    print("  - 7 条路由规则 (覆盖常见路由场景)")
    print()

    # 导入并运行数据源创建脚本
    from create_test_data_sources import main as create_data_sources
    print("\n" + "=" * 60)
    print("第 1 步：创建数据源")
    print("=" * 60)
    await create_data_sources()

    print("\n⏳ 等待 2 秒...")
    await asyncio.sleep(2)

    # 导入并运行目标系统创建脚本
    from create_test_target_systems import main as create_target_systems
    print("\n" + "=" * 60)
    print("第 2 步：创建目标系统")
    print("=" * 60)
    await create_target_systems()

    print("\n⏳ 等待 2 秒...")
    await asyncio.sleep(2)

    # 导入并运行路由规则创建脚本
    from create_simple_routing_rules import main as create_routing_rules
    print("\n" + "=" * 60)
    print("第 3 步：创建路由规则")
    print("=" * 60)
    await create_routing_rules()

    print("\n" + "=" * 60)
    print("✅ 所有测试数据创建完成！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("  1. 访问前端界面查看创建的数据: http://localhost:3001")
    print("     - 数据源管理: /data-sources")
    print("     - 目标系统管理: /target-systems")
    print("     - 路由规则管理: /routing-rules")
    print("  2. 启动数据源适配器开始接收数据")
    print("  3. 发送测试数据验证完整流程:")
    print("     uv run python scripts/quick_udp_test.py")
    print("  4. 查看监控和日志: http://localhost:3001/monitoring")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
