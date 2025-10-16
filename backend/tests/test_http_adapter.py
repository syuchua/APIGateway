"""
HTTP协议适配器测试
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from app.core.eventbus import get_eventbus, reset_eventbus, TopicCategory
from app.core.gateway.adapters.http_adapter import HTTPAdapter, HTTPAdapterConfig
from app.schemas.common import ProtocolType


@pytest.fixture
def clean_eventbus():
    """清理EventBus单例"""
    reset_eventbus()
    yield
    reset_eventbus()


@pytest.fixture
def eventbus(clean_eventbus):
    """创建EventBus实例"""
    return get_eventbus()


@pytest.fixture
def http_config():
    """HTTP适配器配置"""
    return {
        "name": "测试HTTP适配器",
        "endpoint": "/api/data",
        "method": "POST",
        "is_active": True
    }


class TestHTTPAdapterConfig:
    """测试HTTP适配器配置"""

    def test_config_with_defaults(self):
        """测试默认配置"""
        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data"
        )

        assert config.name == "测试"
        assert config.endpoint == "/api/data"
        assert config.method == "POST"
        assert config.is_active is True
        assert config.auto_parse is False

    def test_config_custom_method(self):
        """测试自定义HTTP方法"""
        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data",
            method="PUT"
        )

        assert config.method == "PUT"

    def test_config_with_frame_schema(self):
        """测试带帧格式配置"""
        frame_schema_id = uuid4()
        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data",
            frame_schema_id=frame_schema_id,
            auto_parse=True
        )

        assert config.frame_schema_id == frame_schema_id
        assert config.auto_parse is True


class TestHTTPAdapter:
    """测试HTTP适配器"""

    def test_init_with_dict(self, eventbus, http_config):
        """测试用字典初始化"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        assert adapter.http_config.name == "测试HTTP适配器"
        assert adapter.http_config.endpoint == "/api/data"
        assert adapter.http_config.method == "POST"
        assert adapter.eventbus is eventbus
        assert adapter.is_running is False

    def test_init_with_config_object(self, eventbus):
        """测试用配置对象初始化"""
        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data"
        )

        adapter = HTTPAdapter(
            config=config,
            eventbus=eventbus
        )

        assert adapter.http_config.name == "测试"

    @pytest.mark.asyncio
    async def test_receive_data_publishes_event(self, eventbus, http_config):
        """测试接收数据发布事件"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        # 订阅事件
        received_events = []

        def on_http_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.HTTP_RECEIVED, on_http_received)

        # 模拟接收HTTP数据
        test_data = {
            "temperature": 25.5,
            "humidity": 60.0
        }

        await adapter.receive_data(
            data=test_data,
            source_address="192.168.1.100",
            headers={"Content-Type": "application/json"}
        )

        # 验证事件发布
        assert len(received_events) == 1
        event = received_events[0]

        assert event["source_protocol"] == ProtocolType.HTTP
        assert event["source_address"] == "192.168.1.100"
        assert event["adapter_name"] == "测试HTTP适配器"
        assert event["raw_data"] == test_data
        assert "message_id" in event
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_receive_data_with_parsing(self, eventbus):
        """测试接收字节数据并自动解析（仅适用于特殊场景）"""
        # 注意：HTTP协议通常传输JSON/XML等结构化数据，不需要帧解析
        # 此测试仅验证当配置了帧格式时的兼容性

        from app.schemas.frame_schema import FrameSchemaResponse, FieldDefinition
        from app.schemas.common import DataType, ByteOrder, FrameType, ChecksumType

        # 创建帧格式定义
        frame_schema = FrameSchemaResponse(
            id=uuid4(),
            name="温湿度传感器",
            version="1.0",
            description="温湿度数据",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="temperature",
                    offset=0,
                    length=4,
                    data_type=DataType.FLOAT32,
                    byte_order=ByteOrder.LITTLE_ENDIAN,
                    description="温度"
                ),
                FieldDefinition(
                    name="humidity",
                    offset=4,
                    length=4,
                    data_type=DataType.FLOAT32,
                    byte_order=ByteOrder.LITTLE_ENDIAN,
                    description="湿度"
                )
            ],
            checksum=None,
            checksum_type=ChecksumType.NONE,
            checksum_offset=0,
            checksum_length=0,
            is_published=False,
            is_active=True
        )

        config = HTTPAdapterConfig(
            name="测试解析",
            endpoint="/api/data",
            auto_parse=True
        )

        adapter = HTTPAdapter(
            config=config,
            eventbus=eventbus,
            frame_schema=frame_schema
        )

        # 订阅解析成功事件
        parsed_events = []

        def on_data_parsed(data, topic, source):
            parsed_events.append(data)

        eventbus.subscribe(TopicCategory.DATA_PARSED, on_data_parsed)

        # 发送原始字节数据
        import struct
        raw_bytes = struct.pack('<ff', 25.5, 60.0)

        await adapter.receive_data(
            data=raw_bytes,
            source_address="192.168.1.100"
        )

        # 验证解析事件
        assert len(parsed_events) == 1
        parsed_event = parsed_events[0]

        assert "parsed_data" in parsed_event
        assert parsed_event["parsed_data"]["temperature"] == pytest.approx(25.5, rel=0.01)
        assert parsed_event["parsed_data"]["humidity"] == pytest.approx(60.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_receive_data_parse_error(self, eventbus):
        """测试解析失败处理"""
        from app.schemas.frame_schema import FrameSchemaResponse, FieldDefinition
        from app.schemas.common import DataType, ByteOrder, FrameType, ChecksumType

        frame_schema = FrameSchemaResponse(
            id=uuid4(),
            name="测试",
            version="1.0",
            description="测试",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="value",
                    offset=0,
                    length=8,
                    data_type=DataType.INT64,
                    byte_order=ByteOrder.LITTLE_ENDIAN,
                    description="值"
                )
            ],
            checksum=None,
            checksum_type=ChecksumType.NONE,
            checksum_offset=0,
            checksum_length=0,
            is_published=False,
            is_active=True
        )

        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data",
            auto_parse=True
        )

        adapter = HTTPAdapter(
            config=config,
            eventbus=eventbus,
            frame_schema=frame_schema
        )

        received_events = []

        def on_http_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.HTTP_RECEIVED, on_http_received)

        # 发送长度不足的数据（应该失败）
        await adapter.receive_data(
            data=b'\x01\x02',  # 只有2字节，需要8字节
            source_address="192.168.1.100"
        )

        # 仍然会发布HTTP_RECEIVED事件，但带parse_error
        assert len(received_events) == 1
        assert "parse_error" in received_events[0]

    @pytest.mark.asyncio
    async def test_start_stop(self, eventbus, http_config):
        """测试启动和停止"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        assert adapter.is_running is False

        await adapter.start()
        assert adapter.is_running is True

        await adapter.stop()
        assert adapter.is_running is False

    @pytest.mark.asyncio
    async def test_restart(self, eventbus, http_config):
        """测试重启"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        await adapter.start()
        assert adapter.is_running is True

        await adapter.restart()
        assert adapter.is_running is True

        await adapter.stop()

    def test_get_stats(self, eventbus, http_config):
        """测试获取统计信息"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        stats = adapter.get_stats()

        assert stats["name"] == "测试HTTP适配器"
        assert stats["is_running"] is False
        assert stats["endpoint"] == "/api/data"
        assert stats["method"] == "POST"
        assert stats["auto_parse"] is False
        assert stats["has_frame_parser"] is False
        assert "messages_received" in stats
        assert "messages_processed" in stats
        assert "errors" in stats

    @pytest.mark.asyncio
    async def test_receive_multiple_requests(self, eventbus, http_config):
        """测试接收多个请求"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 发送多个请求
        for i in range(5):
            await adapter.receive_data(
                data={"index": i},
                source_address=f"192.168.1.{100 + i}"
            )

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, eventbus, http_config):
        """测试并发请求"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 并发发送多个请求
        tasks = []
        for i in range(10):
            task = adapter.receive_data(
                data={"index": i},
                source_address=f"192.168.1.{i}"
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        stats = adapter.get_stats()
        assert stats["messages_received"] == 10

        await adapter.stop()

    def test_get_endpoint_path(self, eventbus, http_config):
        """测试获取端点路径"""
        adapter = HTTPAdapter(
            config=http_config,
            eventbus=eventbus
        )

        assert adapter.get_endpoint_path() == "/api/data"

    def test_supports_method(self, eventbus):
        """测试支持的HTTP方法"""
        config = HTTPAdapterConfig(
            name="测试",
            endpoint="/api/data",
            method="POST"
        )

        adapter = HTTPAdapter(
            config=config,
            eventbus=eventbus
        )

        assert adapter.http_config.method == "POST"
