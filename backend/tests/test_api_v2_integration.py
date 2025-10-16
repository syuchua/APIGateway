"""API v2 集成测试，验证主要端点行为"""
import uuid
import pytest
from httpx import AsyncClient


@pytest.fixture(scope="function")
async def client(async_client: AsyncClient):
    """复用全局异步测试客户端"""
    yield async_client


class TestDataSourceV2API:
    """数据源 v2 API 测试"""

    async def test_list_data_sources_v2(self, client: AsyncClient):
        """测试获取数据源列表"""
        response = await client.get("/api/v2/data-sources", params={"page": 1, "limit": 20})

        assert response.status_code == 200
        data = response.json()

        # 验证 ApiResponse 包装格式
        assert "success" in data
        assert "items" in data
        assert "pagination" in data
        assert "message" in data

        # 验证分页信息
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "total_pages" in pagination

    async def test_create_data_source_v2(self, client: AsyncClient):
        """测试创建数据源（嵌套配置）"""
        # 使用唯一名称避免重复
        unique_name = f"测试UDP数据源-{uuid.uuid4().hex[:8]}"
        new_data_source = {
            "name": unique_name,
            "protocol_type": "UDP",
            "connection_config": {
                "listen_address": "0.0.0.0",
                "listen_port": 8888,
                "max_connections": 100,
                "timeout_seconds": 30,
                "buffer_size": 8192
            },
            "parse_config": {
                "auto_parse": True,
                "frame_schema_id": None,
                "parse_options": {}
            },
            "is_active": True
        }

        response = await client.post("/api/v2/data-sources", json=new_data_source)

        assert response.status_code == 201
        data = response.json()

        # 验证 ApiResponse 格式
        assert data["success"] is True
        assert "data" in data
        assert data["message"] == "数据源创建成功"
        assert data["code"] == 201

        # 验证嵌套配置结构
        created = data["data"]
        assert "connection_config" in created
        assert "parse_config" in created
        assert created["connection_config"]["listen_port"] == 8888
        assert created["parse_config"]["auto_parse"] is True

    async def test_get_data_source_v2(self, client: AsyncClient):
        """测试获取单个数据源详情"""
        # 先创建一个数据源
        unique_name = f"测试数据源详情-{uuid.uuid4().hex[:8]}"
        new_data_source = {
            "name": unique_name,
            "protocol_type": "TCP",
            "connection_config": {
                "listen_address": "127.0.0.1",
                "listen_port": 9999
            },
            "parse_config": {
                "auto_parse": False
            }
        }

        create_response = await client.post("/api/v2/data-sources", json=new_data_source)
        assert create_response.status_code == 201

        created_id = create_response.json()["data"]["id"]

        # 获取详情
        response = await client.get(f"/api/v2/data-sources/{created_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == created_id
        assert data["data"]["name"] == unique_name


class TestTargetSystemV2API:
    """目标系统 v2 API 测试"""

    async def test_list_target_systems_v2(self, client: AsyncClient):
        """测试获取目标系统列表"""
        response = await client.get("/api/v2/target-systems", params={"page": 1, "limit": 20})

        assert response.status_code == 200
        data = response.json()

        # 验证 ApiResponse 包装格式
        assert data["success"] is True
        assert "items" in data
        assert "pagination" in data

    async def test_create_target_system_with_auth_v2(self, client: AsyncClient):
        """测试创建目标系统（含认证配置）"""
        unique_name = f"测试HTTP目标系统-{uuid.uuid4().hex[:8]}"
        new_target = {
            "name": unique_name,
            "protocol_type": "HTTP",
            "endpoint_config": {
                "target_address": "192.168.1.100",
                "target_port": 8080,
                "endpoint_path": "/api/data",
                "use_ssl": False
            },
            "auth_config": {
                "auth_type": "bearer",
                "token": "test-bearer-token-123"
            },
            "forwarder_config": {
                "timeout": 30,
                "retry_count": 3,
                "batch_size": 10,
                "compression": False
            },
            "is_active": True
        }

        response = await client.post("/api/v2/target-systems", json=new_target)

        assert response.status_code == 201
        data = response.json()

        # 验证 ApiResponse 格式
        assert data["success"] is True
        assert data["code"] == 201

        # 验证嵌套配置
        created = data["data"]
        assert "endpoint_config" in created
        assert "auth_config" in created
        assert "forwarder_config" in created

        # 验证认证配置
        assert created["auth_config"]["auth_type"] == "bearer"
        assert created["auth_config"]["token"] == "test-bearer-token-123"

    async def test_create_target_system_with_api_key_auth(self, client: AsyncClient):
        """测试创建目标系统（API Key认证）"""
        unique_name = f"API Key认证目标-{uuid.uuid4().hex[:8]}"
        new_target = {
            "name": unique_name,
            "protocol_type": "HTTP",
            "endpoint_config": {
                "target_address": "api.example.com",
                "target_port": 443,
                "use_ssl": True
            },
            "auth_config": {
                "auth_type": "api_key",
                "api_key": "my-api-key-12345",
                "api_key_header": "X-API-Key"
            }
        }

        response = await client.post("/api/v2/target-systems", json=new_target)

        assert response.status_code == 201
        data = response.json()

        auth_config = data["data"]["auth_config"]
        assert auth_config["auth_type"] == "api_key"
        assert auth_config["api_key"] == "my-api-key-12345"
        assert auth_config["api_key_header"] == "X-API-Key"


class TestRoutingRuleV2API:
    """路由规则 v2 API 测试"""

    async def test_list_routing_rules_simple_v2(self, client: AsyncClient):
        """测试获取路由规则简化列表"""
        response = await client.get("/api/v2/routing-rules/simple", params={
            "page": 1,
            "limit": 20,
            "is_published": True
        })

        assert response.status_code == 200
        data = response.json()

        # 验证 PaginatedResponse 格式
        assert data["success"] is True
        assert "items" in data
        assert "pagination" in data
        assert data["message"] == "获取路由规则列表成功"

        # 如果有数据，验证简化响应格式
        if len(data["items"]) > 0:
            item = data["items"][0]
            # 验证简化字段
            assert "id" in item
            assert "name" in item
            assert "priority" in item
            assert "target_system_ids" in item
            assert "is_active" in item
            assert "is_published" in item
            assert "match_count" in item

            # 简化响应不应包含详细配置
            assert isinstance(item["target_system_ids"], list)

    async def test_list_routing_rules_full_v2(self, client: AsyncClient):
        """测试获取路由规则完整列表"""
        response = await client.get("/api/v2/routing-rules", params={
            "page": 1,
            "limit": 20
        })

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "items" in data

        # 如果有数据，验证完整响应格式
        if len(data["items"]) > 0:
            item = data["items"][0]
            # 完整响应应包含详细配置
            assert "source_config" in item
            assert "pipeline" in item
            assert "target_systems" in item
            assert isinstance(item["target_systems"], list)

    async def test_create_routing_rule_v2(self, client: AsyncClient):
        """测试创建路由规则"""
        # 先创建两个真实的目标系统
        target_systems_data = []
        for i in range(2):
            target = {
                "name": f"测试目标系统{i+1}-{uuid.uuid4().hex[:8]}",
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": f"192.168.1.{100+i}",
                    "target_port": 8080 + i
                }
            }
            target_response = await client.post("/api/v2/target-systems", json=target)
            assert target_response.status_code == 201
            target_systems_data.append(target_response.json()["data"]["id"])

        # 创建路由规则
        unique_name = f"测试路由规则-{uuid.uuid4().hex[:8]}"
        new_rule = {
            "name": unique_name,
            "description": "这是一个测试路由规则",
            "priority": 100,
            "source_config": {
                "protocol_types": ["UDP", "TCP"],
                "data_source_ids": []
            },
            "pipeline": {
                "validate": True,
                "transform": False,
                "filter": {}
            },
            "target_systems": [
                {"id": target_systems_data[0], "enabled": True},
                {"id": target_systems_data[1], "enabled": True}
            ],
            "is_active": True,
            "is_published": False
        }

        response = await client.post("/api/v2/routing-rules", json=new_rule)

        assert response.status_code == 201
        data = response.json()

        # 验证 ApiResponse 格式
        assert data["success"] is True
        assert data["message"] == "路由规则创建成功"
        assert data["code"] == 201

        # 验证创建的规则
        created = data["data"]
        assert created["name"] == unique_name
        assert created["priority"] == 100
        assert created["is_published"] is False

    async def test_publish_routing_rule_v2(self, client: AsyncClient):
        """测试发布路由规则"""
        # 先创建一个真实的目标系统用于测试
        target_system = {
            "name": f"测试目标-{uuid.uuid4().hex[:8]}",
            "protocol_type": "HTTP",
            "endpoint_config": {
                "target_address": "localhost",
                "target_port": 8080
            }
        }
        target_response = await client.post("/api/v2/target-systems", json=target_system)
        assert target_response.status_code == 201
        target_id = target_response.json()["data"]["id"]

        # 创建一个未发布的规则
        new_rule = {
            "name": f"待发布规则-{uuid.uuid4().hex[:8]}",
            "priority": 50,
            "source_config": {"protocol_types": ["HTTP"]},
            "pipeline": {"validate": True},
            "target_systems": [{"id": target_id}],
            "is_published": False
        }

        create_response = await client.post("/api/v2/routing-rules", json=new_rule)
        assert create_response.status_code == 201

        rule_id = create_response.json()["data"]["id"]

        # 发布规则
        publish_response = await client.post(f"/api/v2/routing-rules/{rule_id}/publish")

        assert publish_response.status_code == 200
        data = publish_response.json()

        assert data["success"] is True
        assert data["message"] == "路由规则发布成功"
        assert data["data"]["is_published"] is True

    async def test_unpublish_routing_rule_v2(self, client: AsyncClient):
        """测试取消发布路由规则"""
        # 先创建一个真实的目标系统
        target_system = {
            "name": f"测试目标-{uuid.uuid4().hex[:8]}",
            "protocol_type": "HTTP",
            "endpoint_config": {
                "target_address": "localhost",
                "target_port": 8080
            }
        }
        target_response = await client.post("/api/v2/target-systems", json=target_system)
        assert target_response.status_code == 201
        target_id = target_response.json()["data"]["id"]

        # 创建并发布一个规则
        new_rule = {
            "name": f"待取消发布规则-{uuid.uuid4().hex[:8]}",
            "priority": 50,
            "source_config": {"protocol_types": ["MQTT"]},
            "pipeline": {"validate": True},
            "target_systems": [{"id": target_id}],
            "is_published": True
        }

        create_response = await client.post("/api/v2/routing-rules", json=new_rule)
        rule_id = create_response.json()["data"]["id"]

        # 取消发布
        unpublish_response = await client.post(f"/api/v2/routing-rules/{rule_id}/unpublish")

        assert unpublish_response.status_code == 200
        data = unpublish_response.json()

        assert data["success"] is True
        assert data["message"] == "路由规则取消发布成功"
        assert data["data"]["is_published"] is False


    async def test_reload_routing_rule_v2(self, client: AsyncClient, monkeypatch):
        """测试路由规则重新加载"""
        target_system = {
            "name": f"重载目标-{uuid.uuid4().hex[:8]}",
            "protocol_type": "HTTP",
            "endpoint_config": {
                "target_address": "localhost",
                "target_port": 9000
            }
        }
        target_response = await client.post("/api/v2/target-systems", json=target_system)
        assert target_response.status_code == 201
        target_id = target_response.json()["data"]["id"]

        new_rule = {
            "name": f"重载规则-{uuid.uuid4().hex[:8]}",
            "priority": 60,
            "source_config": {"protocol_types": ["HTTP"]},
            "pipeline": {"validate": True},
            "target_systems": [{"id": target_id}],
            "is_active": True
        }

        create_response = await client.post("/api/v2/routing-rules", json=new_rule)
        assert create_response.status_code == 201
        rule_id = create_response.json()["data"]["id"]

        class DummyGatewayManager:
            def __init__(self):
                self.called_with = None

            async def reload_routing_rule(self, rule):
                self.called_with = rule

        dummy_manager = DummyGatewayManager()
        monkeypatch.setattr(
            "app.api.v2.routing_rules.get_gateway_manager",
            lambda: dummy_manager
        )

        reload_response = await client.post(f"/api/v2/routing-rules/{rule_id}/reload")
        assert reload_response.status_code == 200
        data = reload_response.json()

        assert data["success"] is True
        assert data["data"]["status"] == "reloaded"
        assert dummy_manager.called_with is not None
        assert str(dummy_manager.called_with.id) == rule_id


class TestApiResponseFormat:
    """API 响应格式一致性测试"""

    async def test_error_response_format(self, client: AsyncClient):
        """测试错误响应格式"""
        # 请求不存在的资源（使用有效的UUID格式）
        non_existent_id = str(uuid.uuid4())
        response = await client.get(f"/api/v2/data-sources/{non_existent_id}")

        data = response.json()

        # 错误响应也应该符合 ApiResponse 格式
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data

    async def test_pagination_format_consistency(self, client: AsyncClient):
        """测试分页格式一致性"""
        endpoints = [
            "/api/v2/data-sources",
            "/api/v2/target-systems",
            "/api/v2/routing-rules",
            "/api/v2/routing-rules/simple"
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint, params={"page": 1, "limit": 10})
            assert response.status_code == 200

            data = response.json()

            # 所有分页响应都应该有相同的结构
            assert data["success"] is True
            assert "items" in data
            assert "pagination" in data

            pagination = data["pagination"]
            assert pagination["page"] == 1
            assert pagination["limit"] == 10
            assert "total" in pagination
            assert "total_pages" in pagination


class TestNestedConfigStructure:
    """嵌套配置结构测试"""

    async def test_data_source_nested_config(self, client: AsyncClient):
        """测试数据源嵌套配置完整性"""
        unique_name = f"嵌套配置测试-{uuid.uuid4().hex[:8]}"
        new_data_source = {
            "name": unique_name,
            "protocol_type": "WEBSOCKET",
            "connection_config": {
                "listen_address": "0.0.0.0",
                "listen_port": 8765,
                "max_connections": 50,
                "timeout_seconds": 60,
                "buffer_size": 16384
            },
            "parse_config": {
                "auto_parse": True,
                "frame_schema_id": None,  # 使用None而不是字符串
                "parse_options": {
                    "encoding": "utf-8",
                    "strict": True
                }
            }
        }

        response = await client.post("/api/v2/data-sources", json=new_data_source)
        assert response.status_code == 201

        created = response.json()["data"]

        # 验证所有嵌套字段都被正确保存
        conn_config = created["connection_config"]
        assert conn_config["listen_address"] == "0.0.0.0"
        assert conn_config["listen_port"] == 8765
        assert conn_config["max_connections"] == 50
        assert conn_config["timeout_seconds"] == 60
        assert conn_config["buffer_size"] == 16384

        parse_config = created["parse_config"]
        assert parse_config["auto_parse"] is True
        assert "parse_options" in parse_config

    async def test_target_system_all_auth_types(self, client: AsyncClient):
        """测试所有认证类型"""
        auth_types = [
            {
                "auth_type": "basic",
                "username": "admin",
                "password": "password123"
            },
            {
                "auth_type": "bearer",
                "token": "bearer-token-xyz"
            },
            {
                "auth_type": "api_key",
                "api_key": "api-key-abc",
                "api_key_header": "X-Custom-Key"
            },
            {
                "auth_type": "custom",
                "custom_headers": {
                    "X-Custom-Auth": "custom-value",
                    "X-Request-ID": "12345"
                }
            },
            {
                "auth_type": "none"
            }
        ]

        for i, auth_config in enumerate(auth_types):
            unique_name = f"认证测试{i+1}-{uuid.uuid4().hex[:8]}"
            target = {
                "name": unique_name,
                "protocol_type": "HTTP",
                "endpoint_config": {
                    "target_address": f"server{i+1}.example.com",
                    "target_port": 443,
                    "use_ssl": True
                },
                "auth_config": auth_config
            }

            response = await client.post("/api/v2/target-systems", json=target)
            assert response.status_code == 201, f"Failed for auth_type: {auth_config['auth_type']}"

            created_auth = response.json()["data"]["auth_config"]
            assert created_auth["auth_type"] == auth_config["auth_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
