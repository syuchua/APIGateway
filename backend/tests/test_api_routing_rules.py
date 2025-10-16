"""
路由规则管理API测试
"""
import pytest
from uuid import UUID, uuid4
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
class TestRoutingRuleAPI:
    """路由规则API测试"""

    @pytest.mark.asyncio
    async def test_create_routing_rule(self, async_client):
        """测试创建路由规则"""
        # 首先创建两个目标系统用于路由规则
        target_data_1 = {
            "name": "测试目标系统1",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9001,
            "endpoint_path": "/api/data1",
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data_1)
        assert response.status_code == 201
        target1_id = response.json()["id"]

        target_data_2 = {
            "name": "测试目标系统2",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9002,
            "endpoint_path": "/api/data2",
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data_2)
        assert response.status_code == 201
        target2_id = response.json()["id"]

        # 创建路由规则
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
            "logical_operator": "AND",
            "target_system_ids": [target1_id, target2_id],
            "is_published": False
        }

        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        assert response.status_code == 201

        result = response.json()
        assert result["name"] == rule_data["name"]
        assert result["description"] == rule_data["description"]
        assert result["priority"] == 80
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["field_path"] == "parsed_data.temperature"
        assert result["conditions"][0]["operator"] == ">"
        assert result["conditions"][0]["value"] == 30
        assert result["logical_operator"] == "AND"
        assert len(result["target_system_ids"]) == 2
        assert result["is_active"] is True
        assert result["is_published"] is False
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_create_routing_rule_with_multiple_conditions(self, async_client):
        """测试创建包含多个条件的路由规则"""
        # 创建目标系统
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9003,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        # 创建包含多个条件的路由规则
        rule_data = {
            "name": "复杂条件路由",
            "priority": 60,
            "conditions": [
                {
                    "field_path": "parsed_data.temperature",
                    "operator": ">",
                    "value": 25
                },
                {
                    "field_path": "parsed_data.humidity",
                    "operator": "<",
                    "value": 60
                },
                {
                    "field_path": "parsed_data.device_id",
                    "operator": "in",
                    "value": ["device-001", "device-002"]
                }
            ],
            "logical_operator": "OR",
            "target_system_ids": [target_id]
        }

        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        assert response.status_code == 201

        result = response.json()
        assert len(result["conditions"]) == 3
        assert result["logical_operator"] == "OR"

    @pytest.mark.asyncio
    async def test_create_routing_rule_validation_error(self, async_client):
        """测试创建路由规则验证失败"""
        # 缺少必填字段target_system_ids
        rule_data = {
            "name": "无效路由规则",
            "priority": 50,
        }

        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_routing_rules(self, async_client):
        """测试获取路由规则列表"""
        response = await async_client.get("/api/v1/routing-rules/")
        assert response.status_code == 200

        results = response.json()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_list_routing_rules_with_filters(self, async_client):
        """测试使用过滤器获取路由规则列表"""
        # 测试is_published过滤
        response = await async_client.get("/api/v1/routing-rules/?is_published=true")
        assert response.status_code == 200

        # 测试is_active过滤
        response = await async_client.get("/api/v1/routing-rules/?is_active=true")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_routing_rule_by_id(self, async_client):
        """测试根据ID获取路由规则详情"""
        # 先创建一个路由规则
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9004,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        rule_data = {
            "name": "测试路由规则",
            "priority": 70,
            "target_system_ids": [target_id]
        }
        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        rule_id = response.json()["id"]

        # 获取详情
        response = await async_client.get(f"/api/v1/routing-rules/{rule_id}")
        assert response.status_code == 200

        result = response.json()
        assert result["id"] == rule_id
        assert result["name"] == "测试路由规则"

    @pytest.mark.asyncio
    async def test_get_routing_rule_not_found(self, async_client):
        """测试获取不存在的路由规则"""
        non_existent_id = str(uuid4())
        response = await async_client.get(f"/api/v1/routing-rules/{non_existent_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_routing_rule(self, async_client):
        """测试更新路由规则"""
        # 创建路由规则
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9005,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        rule_data = {
            "name": "原始路由规则",
            "priority": 50,
            "target_system_ids": [target_id]
        }
        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        rule_id = response.json()["id"]

        # 更新路由规则
        update_data = {
            "name": "更新后的路由规则",
            "priority": 90,
            "description": "更新后的描述",
            "conditions": [
                {
                    "field_path": "parsed_data.status",
                    "operator": "==",
                    "value": "error"
                }
            ]
        }

        response = await async_client.put(f"/api/v1/routing-rules/{rule_id}", json=update_data)
        assert response.status_code == 200

        result = response.json()
        assert result["name"] == "更新后的路由规则"
        assert result["priority"] == 90
        assert result["description"] == "更新后的描述"
        assert len(result["conditions"]) == 1

    @pytest.mark.asyncio
    async def test_update_routing_rule_not_found(self, async_client):
        """测试更新不存在的路由规则"""
        non_existent_id = str(uuid4())
        update_data = {"name": "更新路由规则"}

        response = await async_client.put(f"/api/v1/routing-rules/{non_existent_id}", json=update_data)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_routing_rule(self, async_client):
        """测试发布路由规则"""
        # 创建路由规则
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9006,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        rule_data = {
            "name": "待发布路由规则",
            "priority": 50,
            "target_system_ids": [target_id],
            "is_published": False
        }
        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        rule_id = response.json()["id"]

        # 发布路由规则
        response = await async_client.post(f"/api/v1/routing-rules/{rule_id}/publish")
        assert response.status_code == 200

        result = response.json()
        assert result["is_published"] is True

    @pytest.mark.asyncio
    async def test_unpublish_routing_rule(self, async_client):
        """测试取消发布路由规则"""
        # 创建并发布路由规则
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9007,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        rule_data = {
            "name": "已发布路由规则",
            "priority": 50,
            "target_system_ids": [target_id],
            "is_published": True
        }
        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        rule_id = response.json()["id"]

        # 取消发布
        response = await async_client.post(f"/api/v1/routing-rules/{rule_id}/unpublish")
        assert response.status_code == 200

        result = response.json()
        assert result["is_published"] is False

    @pytest.mark.asyncio
    async def test_delete_routing_rule(self, async_client):
        """测试删除路由规则"""
        # 创建路由规则
        target_data = {
            "name": "测试目标系统",
            "protocol_type": "http",
            "target_address": "localhost",
            "target_port": 9008,
        }
        response = await async_client.post("/api/v1/target-systems/", json=target_data)
        target_id = response.json()["id"]

        rule_data = {
            "name": "待删除路由规则",
            "priority": 50,
            "target_system_ids": [target_id]
        }
        response = await async_client.post("/api/v1/routing-rules/", json=rule_data)
        rule_id = response.json()["id"]

        # 删除路由规则
        response = await async_client.delete(f"/api/v1/routing-rules/{rule_id}")
        assert response.status_code == 204

        # 验证已删除
        response = await async_client.get(f"/api/v1/routing-rules/{rule_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_routing_rule_not_found(self, async_client):
        """测试删除不存在的路由规则"""
        non_existent_id = str(uuid4())
        response = await async_client.delete(f"/api/v1/routing-rules/{non_existent_id}")
        assert response.status_code == 404
