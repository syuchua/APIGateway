"""
数据处理管道测试用例
采用TDD方法测试数据处理管道的核心功能
"""
import json
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from app.core.gateway.pipeline.data_pipeline import DataPipeline
from app.core.eventbus import get_eventbus, TopicCategory
from app.schemas.common import ProtocolType, FrameType, DataType, ByteOrder, ChecksumType
from app.schemas.frame_schema import FrameSchemaResponse, FieldDefinition
from app.schemas.routing_rule import RoutingRuleResponse, ConditionOperator
from app.schemas.target_system import TargetSystemResponse
from app.schemas.forwarder import ForwardStatus
from app.services.crypto_service import get_crypto_service


class TestDataPipeline:
    """测试数据处理管道"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def frame_schema(self):
        """创建完整的帧格式定义"""
        return FrameSchemaResponse(
            id=uuid4(),
            name="温度传感器帧",
            version="1.0.0",
            description="温度传感器数据帧",
            protocol=ProtocolType.UDP,
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            is_active=True,
            is_published=True,
            fields=[
                FieldDefinition(
                    name="temperature",
                    offset=0,
                    length=4,
                    data_type=DataType.FLOAT32,
                    byte_order=ByteOrder.LITTLE_ENDIAN
                ),
                FieldDefinition(
                    name="humidity",
                    offset=4,
                    length=4,
                    data_type=DataType.FLOAT32,
                    byte_order=ByteOrder.LITTLE_ENDIAN
                )
            ],
            checksum_type=ChecksumType.NONE,
            checksum_offset=None,
            checksum_length=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def routing_rule(self):
        """创建路由规则"""
        from app.schemas.routing_rule import LogicalOperator
        target_id = uuid4()
        return RoutingRuleResponse(
            id=uuid4(),
            name="高温报警路由",
            description="温度超过30度发送到报警系统",
            priority=1,
            is_active=True,
            is_published=True,
            logical_operator=LogicalOperator.AND,
            conditions=[{
                "field_path": "parsed_data.temperature",
                "operator": ConditionOperator.GREATER_THAN,
                "value": 30.0
            }],
            source_config={
                "protocols": ["UDP"],
                "source_ids": [],
                "pattern": "*"
            },
            pipeline={
                "parser": {"enabled": True, "type": "auto"},
                "validator": {"enabled": False},
                "transformer": {"enabled": False}
            },
            target_system_ids=[target_id],
            target_systems=[{"id": target_id}],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def target_system(self):
        """创建目标系统"""
        return TargetSystemResponse(
            id=uuid4(),
            name="报警系统",
            description="高温报警接收系统",
            protocol_type=ProtocolType.HTTP,
            target_address="localhost",
            target_port=8888,
            is_active=True,
            endpoint_path="/api/alert",
            timeout=30,
            retry_count=3,
            batch_size=1,
            transform_config={
                "field_mapping": {
                    "parsed_data.temperature": "temp",
                    "parsed_data.humidity": "hum"
                },
                "add_fields": {
                    "alert_type": "high_temperature"
                }
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    async def pipeline(self, eventbus):
        """创建数据处理管道"""
        pipeline = DataPipeline(eventbus)
        yield pipeline
        # 清理
        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline, eventbus):
        """测试管道初始化"""
        assert pipeline.eventbus == eventbus
        assert pipeline.is_running is False
        assert pipeline.frame_parsers is not None
        assert pipeline.routing_engine is not None
        assert pipeline.forwarder_manager is not None

    @pytest.mark.asyncio
    async def test_start_stop_pipeline(self, pipeline):
        """测试启动和停止管道"""
        # 启动管道
        await pipeline.start()
        assert pipeline.is_running is True

        # 停止管道
        await pipeline.stop()
        assert pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_register_frame_schema(self, pipeline, frame_schema):
        """测试注册帧格式"""
        await pipeline.start()
        await pipeline.register_frame_schema(frame_schema)

        # 验证已注册
        assert str(frame_schema.id) in pipeline.frame_parsers

    @pytest.mark.asyncio
    async def test_register_routing_rule(self, pipeline, routing_rule):
        """测试注册路由规则"""
        await pipeline.start()
        await pipeline.register_routing_rule(routing_rule)

        # 验证已注册（rules是列表，检查规则对象在列表中）
        assert any(r.id == routing_rule.id for r in pipeline.routing_engine.rules)

    @pytest.mark.asyncio
    async def test_register_target_system(self, pipeline, target_system):
        """测试注册目标系统"""
        await pipeline.start()
        await pipeline.register_target_system(target_system)

        # 验证已注册
        assert str(target_system.id) in pipeline.forwarder_manager.target_systems

    def test_decrypt_encrypted_payload(self, pipeline):
        """测试加密消息解密"""
        crypto = get_crypto_service()
        payload = {"temperature": 32.5, "unit": "C"}
        encrypted = crypto.encrypt_message(json.dumps(payload).encode("utf-8"))

        message = {
            "encrypted_payload": encrypted,
            "message_id": "enc-1"
        }

        pipeline._decrypt_message_if_needed(message)

        assert message.get("is_encrypted") is True
        assert message.get("parsed_data") == payload
        assert json.loads(message.get("raw_text")) == payload

    @pytest.mark.asyncio
    async def test_unregister_components(self, pipeline, frame_schema, routing_rule, target_system):
        """测试注销管道组件"""
        await pipeline.start()

        # 注册
        await pipeline.register_frame_schema(frame_schema)
        await pipeline.register_routing_rule(routing_rule)
        await pipeline.register_target_system(target_system)

        # 注销
        await pipeline.unregister_frame_schema(frame_schema.id)
        await pipeline.unregister_routing_rule(routing_rule.id)
        await pipeline.unregister_target_system(target_system.id)

        # 验证已注销
        assert str(frame_schema.id) not in pipeline.frame_parsers
        assert not any(r.id == routing_rule.id for r in pipeline.routing_engine.rules)
        assert str(target_system.id) not in pipeline.forwarder_manager.target_systems

    @pytest.mark.asyncio
    async def test_manual_process_message(self, clean_eventbus, pipeline, frame_schema, routing_rule, target_system):
        """测试手动处理消息（不启动自动转发）"""
        # 注意：不调用 pipeline.start() 以避免自动转发干扰

        # 注册组件
        await pipeline.register_frame_schema(frame_schema)

        # 修改路由规则使用正确的target_system
        routing_rule.target_system_ids = [target_system.id]
        routing_rule.target_systems = [{"id": target_system.id}]
        await pipeline.register_routing_rule(routing_rule)
        await pipeline.register_target_system(target_system)

        # Mock转发器
        mock_forwarder = AsyncMock()
        mock_result = Mock()
        mock_result.status = ForwardStatus.SUCCESS
        mock_result.status_code = 200
        mock_forwarder.forward.return_value = mock_result
        pipeline.forwarder_manager.forwarders[str(target_system.id)] = mock_forwarder

        # 发送数据（温度35度，湿度60%）
        import struct
        raw_data = struct.pack('<ff', 35.0, 60.0)

        # 手动处理消息
        result = await pipeline.process_message(
            raw_data=raw_data,
            frame_schema_id=frame_schema.id,
            source_info={
                "message_id": str(uuid4()),
                "source_protocol": ProtocolType.UDP,
                "source_id": "sensor_001"
            }
        )

        # 验证处理成功
        assert result["success"] is True
        assert result["stage"] == "complete"

        # 验证数据转换正确
        mock_forwarder.forward.assert_called_once()
        call_args = mock_forwarder.forward.call_args[0][0]
        assert "temp" in call_args
        assert call_args["temp"] == 35.0
        assert call_args["hum"] == 60.0
        assert call_args["alert_type"] == "high_temperature"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
