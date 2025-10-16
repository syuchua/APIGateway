"""
路由规则API快速验证脚本
"""
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def test_routing_rules_api():
    """快速测试路由规则API"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        # 1. 创建目标系统用于测试
        print("1. 创建测试目标系统...")
        target_data = {
            "name": "测试告警系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9001,
            "endpoint_path": "/api/alert",
        }
        response = await client.post("/api/v1/target-systems/", json=target_data)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 201:
            target_id = response.json()["id"]
            print(f"   目标系统ID: {target_id}")
        else:
            print(f"   错误: {response.text}")
            return

        # 2. 创建路由规则
        print("\n2. 创建路由规则...")
        rule_data = {
            "name": "温度告警路由",
            "description": "温度超过30度的数据路由到告警系统",
            "priority": 80,
            "conditions": [
                {
                    "field_path": "parsed_data.temperature",
                    "operator": ">",
                    "value": 30
                }
            ],
            "logical_operator": "and",  # 测试小写输入
            "target_system_ids": [target_id],
            "is_published": False
        }
        response = await client.post("/api/v1/routing-rules/", json=rule_data)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            rule_id = result["id"]
            print(f"   路由规则ID: {rule_id}")
            print(f"   名称: {result['name']}")
            print(f"   优先级: {result['priority']}")
            print(f"   逻辑运算符: {result['logical_operator']}")  # 应该是大写AND
            print(f"   条件数量: {len(result['conditions'])}")
            print(f"   是否发布: {result['is_published']}")
        else:
            print(f"   错误: {response.text}")
            return

        # 3. 获取路由规则列表
        print("\n3. 获取路由规则列表...")
        response = await client.get("/api/v1/routing-rules/")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            rules = response.json()
            print(f"   总数: {len(rules)}")
        else:
            print(f"   错误: {response.text}")

        # 4. 获取路由规则详情
        print("\n4. 获取路由规则详情...")
        response = await client.get(f"/api/v1/routing-rules/{rule_id}")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   名称: {result['name']}")
            print(f"   描述: {result['description']}")
        else:
            print(f"   错误: {response.text}")

        # 5. 更新路由规则
        print("\n5. 更新路由规则...")
        update_data = {
            "name": "更新后的温度告警路由",
            "priority": 90,
            "conditions": [
                {
                    "field_path": "parsed_data.temperature",
                    "operator": ">=",
                    "value": 35
                },
                {
                    "field_path": "parsed_data.humidity",
                    "operator": "<",
                    "value": 60
                }
            ],
            "logical_operator": "or"  # 测试小写输入
        }
        response = await client.put(f"/api/v1/routing-rules/{rule_id}", json=update_data)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   更新后名称: {result['name']}")
            print(f"   更新后优先级: {result['priority']}")
            print(f"   更新后逻辑运算符: {result['logical_operator']}")  # 应该是大写OR
            print(f"   更新后条件数量: {len(result['conditions'])}")
        else:
            print(f"   错误: {response.text}")

        # 6. 发布路由规则
        print("\n6. 发布路由规则...")
        response = await client.post(f"/api/v1/routing-rules/{rule_id}/publish")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   发布状态: {result['is_published']}")
        else:
            print(f"   错误: {response.text}")

        # 7. 取消发布路由规则
        print("\n7. 取消发布路由规则...")
        response = await client.post(f"/api/v1/routing-rules/{rule_id}/unpublish")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   发布状态: {result['is_published']}")
        else:
            print(f"   错误: {response.text}")

        # 8. 删除路由规则
        print("\n8. 删除路由规则...")
        response = await client.delete(f"/api/v1/routing-rules/{rule_id}")
        print(f"   状态码: {response.status_code}")

        # 9. 验证已删除
        print("\n9. 验证路由规则已删除...")
        response = await client.get(f"/api/v1/routing-rules/{rule_id}")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 404:
            print("   ✓ 路由规则已成功删除")

        # 10. 清理测试目标系统
        print("\n10. 清理测试目标系统...")
        response = await client.delete(f"/api/v1/target-systems/{target_id}")
        print(f"   状态码: {response.status_code}")

        print("\n✓ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(test_routing_rules_api())
