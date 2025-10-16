"""
转发器管理器测试用例
采用TDD方法测试转发器管理和调度功能
"""
import json
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.core.gateway.forwarder.forwarder_manager import ForwarderManager
from app.core.eventbus import get_eventbus, TopicCategory
from app.schemas.target_system import TargetSystemResponse
from app.schemas.forwarder import HTTPForwarderConfig, HTTPMethod, ForwardStatus
from app.schemas.common import ProtocolType
from app.core.gateway.pipeline.transformer import TransformConfig
from app.services.crypto_service import get_crypto_service


class TestForwarderManager:
    """测试转发器管理器"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def http_target_system(self):
        """创建HTTP目标系统"""
        return TargetSystemResponse(
            id=uuid4(),
            name="HTTP目标系统",
            description="测试HTTP目标",
            protocol_type=ProtocolType.HTTP,
            target_address="localhost",
            target_port=8888,
            endpoint_path="/api/data",
            is_active=True,
            timeout=30,
            retry_count=3,
            batch_size=1,
            transform_config={
                "flatten_parsed_data": True,
                "remove_fields": ["raw_data"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    async def manager(self, eventbus):
        """创建转发器管理器"""
        manager = ForwarderManager(eventbus)
        yield manager
        # 清理
        await manager.close()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager, eventbus):
        """测试管理器初始化"""
        assert manager.eventbus == eventbus
        assert len(manager.forwarders) == 0
        assert len(manager.target_systems) == 0

    @pytest.mark.asyncio
    async def test_register_target_system(self, manager, http_target_system):
        """测试注册目标系统"""
        await manager.register_target_system(http_target_system)

        # 验证目标系统已注册
        assert str(http_target_system.id) in manager.target_systems
        assert str(http_target_system.id) in manager.forwarders

        # 验证转发器已创建
        forwarder = manager.forwarders[str(http_target_system.id)]
        assert forwarder is not None

    @pytest.mark.asyncio
    async def test_unregister_target_system(self, manager, http_target_system):
        """测试注销目标系统"""
        # 先注册
        await manager.register_target_system(http_target_system)
        assert str(http_target_system.id) in manager.target_systems

        # 注销
        await manager.unregister_target_system(http_target_system.id)

        # 验证已注销
        assert str(http_target_system.id) not in manager.target_systems
        assert str(http_target_system.id) not in manager.forwarders

    @pytest.mark.asyncio
    async def test_forward_to_single_target(self, manager, http_target_system):
        """测试转发到单个目标系统"""
        await manager.register_target_system(http_target_system)

        # Mock HTTP转发器
        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.SUCCESS
        mock_result.status_code = 200
        mock_forwarder.forward.return_value = mock_result

        manager.forwarders[str(http_target_system.id)] = mock_forwarder

        # 转发数据
        data = {
            "message_id": "test-123",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0
            },
            "raw_data": b"test"
        }

        target_ids = [http_target_system.id]
        results = await manager.forward_to_targets(data, target_ids)

        # 验证转发成功
        assert len(results) == 1
        assert results[0]["target_id"] == str(http_target_system.id)
        assert results[0]["status"] == ForwardStatus.SUCCESS

        # 验证转发器被调用
        mock_forwarder.forward.assert_called_once()
        # 验证数据被转换（raw_data应该被移除）
        call_args = mock_forwarder.forward.call_args[0][0]
        assert "raw_data" not in call_args

    @pytest.mark.asyncio
    async def test_forward_with_encryption_enabled(self, manager, http_target_system):
        """测试目标配置启用加密时的转发"""
        http_target_system.forwarder_config = {
            "timeout": 30,
            "retry_count": 3,
            "batch_size": 1,
            "encryption": {"enabled": True, "metadata": {"tenant": "demo"}}
        }
        http_target_system.transform_config = None

        await manager.register_target_system(http_target_system)

        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.SUCCESS
        mock_result.status_code = 200
        mock_forwarder.forward.return_value = mock_result
        manager.forwarders[str(http_target_system.id)] = mock_forwarder

        message = {
            "message_id": "enc-test",
            "parsed_data": {"value": 102.5},
            "raw_data": b"binary",
            "timestamp": datetime(2025, 1, 1, 12, 0, 0)
        }

        results = await manager.forward_to_targets(message, [http_target_system.id])

        assert results[0]["status"] == ForwardStatus.SUCCESS

        forwarded_payload = mock_forwarder.forward.call_args[0][0]
        assert "encrypted_payload" in forwarded_payload
        assert forwarded_payload["encryption"]["tenant"] == "demo"

        crypto = get_crypto_service()
        decrypted = crypto.decrypt_message(forwarded_payload["encrypted_payload"])
        decoded = json.loads(decrypted.decode("utf-8"))
        assert decoded.get("message_id") == "enc-test"
        assert decoded.get("target_id") == str(http_target_system.id)
        assert decoded.get("parsed_data", {}).get("value") == 102.5


    @pytest.mark.asyncio
    async def test_forward_to_multiple_targets(self, manager):
        """测试转发到多个目标系统"""
        # 创建多个目标系统
        target1 = TargetSystemResponse(
            id=uuid4(),
            name="目标1",
            description="测试",
            protocol_type=ProtocolType.HTTP,
            target_address="api1.example.com",
            target_port=80,
            endpoint_path="/api/endpoint1",
            is_active=True,
            timeout=30,
            retry_count=3,
            batch_size=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        target2 = TargetSystemResponse(
            id=uuid4(),
            name="目标2",
            description="测试",
            protocol_type=ProtocolType.HTTP,
            target_address="api2.example.com",
            target_port=80,
            endpoint_path="/api/endpoint2",
            is_active=True,
            timeout=30,
            retry_count=3,
            batch_size=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        await manager.register_target_system(target1)
        await manager.register_target_system(target2)

        # Mock转发器
        for target_id in [str(target1.id), str(target2.id)]:
            mock_forwarder = AsyncMock()
            mock_result = Mock()
            mock_result.status = ForwardStatus.SUCCESS
            mock_result.status_code = 200
            mock_forwarder.forward.return_value = mock_result
            manager.forwarders[target_id] = mock_forwarder

        # 转发到两个目标
        data = {"message_id": "test-123", "value": 100}
        target_ids = [target1.id, target2.id]

        results = await manager.forward_to_targets(data, target_ids)

        # 验证都转发成功
        assert len(results) == 2
        assert all(r["status"] == ForwardStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_forward_with_transformation(self, manager, http_target_system):
        """测试转发时进行数据转换"""
        # 配置数据转换
        http_target_system.transform_config = {
            "field_mapping": {
                "parsed_data.temperature": "temp",
                "parsed_data.humidity": "hum"
            },
            "remove_fields": ["raw_data", "message_id"],
            "add_fields": {
                "device_type": "sensor"
            },
            "flatten_parsed_data": False
        }

        await manager.register_target_system(http_target_system)

        # Mock转发器
        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.SUCCESS
        mock_forwarder.forward.return_value = mock_result
        manager.forwarders[str(http_target_system.id)] = mock_forwarder

        # 原始数据
        data = {
            "message_id": "test-123",
            "raw_data": b"binary",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0
            }
        }

        await manager.forward_to_targets(data, [http_target_system.id])

        # 验证转换后的数据
        call_args = mock_forwarder.forward.call_args[0][0]
        assert "temp" in call_args
        assert "hum" in call_args
        assert call_args["temp"] == 25.5
        assert call_args["hum"] == 60.0
        assert call_args["device_type"] == "sensor"
        assert "raw_data" not in call_args
        assert "message_id" not in call_args

    @pytest.mark.asyncio
    async def test_handle_forward_failure(self, manager, http_target_system):
        """测试处理转发失败"""
        await manager.register_target_system(http_target_system)

        # Mock转发器返回失败
        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.FAILED
        mock_result.error = "Connection refused"
        mock_forwarder.forward.return_value = mock_result
        manager.forwarders[str(http_target_system.id)] = mock_forwarder

        data = {"message_id": "test-123"}
        results = await manager.forward_to_targets(data, [http_target_system.id])

        # 验证失败被记录
        assert len(results) == 1
        assert results[0]["status"] == ForwardStatus.FAILED
        assert results[0]["error"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_handle_nonexistent_target(self, manager):
        """测试处理不存在的目标系统"""
        nonexistent_id = uuid4()

        data = {"message_id": "test-123"}
        results = await manager.forward_to_targets(data, [nonexistent_id])

        # 验证错误被处理
        assert len(results) == 1
        assert results[0]["status"] == ForwardStatus.FAILED
        assert "not found" in results[0]["error"].lower()

    @pytest.mark.asyncio
    async def test_auto_forward_on_routing_decided(self, manager, http_target_system):
        """测试自动转发（订阅ROUTING_DECIDED主题）"""
        await manager.register_target_system(http_target_system)

        # Mock转发器
        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.SUCCESS
        mock_forwarder.forward.return_value = mock_result
        manager.forwarders[str(http_target_system.id)] = mock_forwarder

        # 启动自动转发
        manager.start_auto_forward()

        # 收集转发结果
        forwarded_messages = []

        def forward_handler(data, topic, source):
            forwarded_messages.append(data)

        manager.eventbus.subscribe(TopicCategory.DATA_FORWARDED, forward_handler)

        # 模拟路由决策结果
        routing_result = {
            "message_id": "test-123",
            "parsed_data": {"temperature": 25.5},
            "target_system_ids": [str(http_target_system.id)]
        }

        manager.eventbus.publish(
            topic=TopicCategory.ROUTING_DECIDED,
            data=routing_result,
            source="test"
        )

        # 等待异步处理
        await asyncio.sleep(0.2)

        # 验证自动转发
        assert len(forwarded_messages) == 1
        assert forwarded_messages[0]["message_id"] == "test-123"

        manager.stop_auto_forward()

    @pytest.mark.asyncio
    async def test_get_statistics(self, manager, http_target_system):
        """测试获取统计信息"""
        await manager.register_target_system(http_target_system)

        stats = manager.get_stats()

        assert stats["total_targets"] == 1
        assert stats["active_targets"] == 1
        assert stats["total_forwarders"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
