"""
数据源管理API测试
"""
import pytest
from uuid import uuid4


class TestDataSourceAPI:
    """数据源API测试"""

    @pytest.mark.asyncio
    async def test_create_data_source(self, async_client):
        """测试创建数据源"""
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

        response = await async_client.post("/api/v1/data-sources", json=data)
        assert response.status_code == 201

        result = response.json()
        assert result["name"] == data["name"]
        assert result["protocol_type"] == "UDP"  # API返回大写
        assert result["is_active"] is True
        assert "id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_data_source_validation_error(self, async_client):
        """测试创建数据源参数验证"""
        # 缺少必填字段
        data = {
            "name": "测试源",
            # 缺少protocol_type
        }

        response = await async_client.post("/api/v1/data-sources", json=data)
        assert response.status_code == 422  # Validation Error

    @pytest.mark.asyncio
    async def test_list_data_sources(self, async_client):
        """测试获取数据源列表"""
        # 先创建几个数据源
        for i in range(3):
            data = {
                "name": f"测试源{i}",
                "protocol_type": "udp",
                "listen_address": "0.0.0.0",
                "listen_port": 8000 + i,
                "auto_parse": True,
                "max_connections": 100,
                "timeout_seconds": 30,
                "buffer_size": 8192,
            }
            await async_client.post("/api/v1/data-sources", json=data)

        # 获取列表
        response = await async_client.get("/api/v1/data-sources")
        assert response.status_code == 200

        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_list_data_sources_with_filters(self, async_client):
        """测试过滤数据源列表"""
        # 创建不同协议的数据源
        await async_client.post("/api/v1/data-sources", json={
            "name": "UDP源",
            "protocol_type": "udp",
            "listen_address": "0.0.0.0",
            "listen_port": 8001,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        })

        await async_client.post("/api/v1/data-sources", json={
            "name": "HTTP源",
            "protocol_type": "http",
            "listen_address": "0.0.0.0",
            "listen_port": 8002,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        })

        # 按协议过滤
        response = await async_client.get("/api/v1/data-sources?protocol=udp")
        assert response.status_code == 200

        result = response.json()
        assert all(ds["protocol_type"] == "UDP" for ds in result)  # API返回大写

    @pytest.mark.asyncio
    async def test_get_data_source_by_id(self, async_client):
        """测试获取单个数据源"""
        # 创建数据源
        create_response = await async_client.post("/api/v1/data-sources", json={
            "name": "测试源",
            "protocol_type": "tcp",
            "listen_address": "0.0.0.0",
            "listen_port": 8005,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        })
        created = create_response.json()
        source_id = created["id"]

        # 获取详情
        response = await async_client.get(f"/api/v1/data-sources/{source_id}")
        assert response.status_code == 200

        result = response.json()
        assert result["id"] == source_id
        assert result["name"] == "测试源"

    @pytest.mark.asyncio
    async def test_get_nonexistent_data_source(self, async_client):
        """测试获取不存在的数据源"""
        fake_id = str(uuid4())
        response = await async_client.get(f"/api/v1/data-sources/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_data_source(self, async_client):
        """测试更新数据源"""
        # 创建数据源
        create_response = await async_client.post("/api/v1/data-sources", json={
            "name": "原始名称",
            "protocol_type": "mqtt",
            "listen_address": "0.0.0.0",
            "listen_port": 1883,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        })
        created = create_response.json()
        source_id = created["id"]

        # 更新
        update_data = {
            "name": "更新后的名称",
            "description": "添加了描述",
            "listen_port": 1884,
        }
        response = await async_client.put(
            f"/api/v1/data-sources/{source_id}",
            json=update_data
        )
        assert response.status_code == 200

        result = response.json()
        assert result["name"] == "更新后的名称"
        assert result["description"] == "添加了描述"

    @pytest.mark.asyncio
    async def test_update_nonexistent_data_source(self, async_client):
        """测试更新不存在的数据源"""
        fake_id = str(uuid4())
        response = await async_client.put(
            f"/api/v1/data-sources/{fake_id}",
            json={"name": "新名称"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_data_source(self, async_client):
        """测试删除数据源"""
        # 创建数据源
        create_response = await async_client.post("/api/v1/data-sources", json={
            "name": "待删除的源",
            "protocol_type": "websocket",
            "listen_address": "0.0.0.0",
            "listen_port": 8003,
            "auto_parse": True,
            "max_connections": 100,
            "timeout_seconds": 30,
            "buffer_size": 8192,
        })
        created = create_response.json()
        source_id = created["id"]

        # 删除
        response = await async_client.delete(f"/api/v1/data-sources/{source_id}")
        assert response.status_code == 204

        # 验证已删除
        get_response = await async_client.get(f"/api/v1/data-sources/{source_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_data_source(self, async_client):
        """测试删除不存在的数据源"""
        fake_id = str(uuid4())
        response = await async_client.delete(f"/api/v1/data-sources/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_pagination(self, async_client):
        """测试分页功能"""
        # 创建多个数据源
        for i in range(15):
            await async_client.post("/api/v1/data-sources", json={
                "name": f"分页测试源{i}",
                "protocol_type": "udp",
                "listen_address": "0.0.0.0",
                "listen_port": 9000 + i,
                "auto_parse": True,
                "max_connections": 100,
                "timeout_seconds": 30,
                "buffer_size": 8192,
            })

        # 测试skip和limit
        response = await async_client.get("/api/v1/data-sources?skip=0&limit=5")
        assert response.status_code == 200
        assert len(response.json()) <= 5

        response = await async_client.get("/api/v1/data-sources?skip=5&limit=5")
        assert response.status_code == 200
        assert len(response.json()) <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
