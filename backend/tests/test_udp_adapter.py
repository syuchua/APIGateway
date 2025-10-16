"""
UDP协议适配器测试用例
采用TDD方法，测试UDP数据接收、解析和EventBus发布功能
"""
import pytest
import asyncio
import socket
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.core.gateway.adapters.udp_adapter import UDPAdapter, UDPAdapterConfig
from app.core.eventbus import get_eventbus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.message import UnifiedMessage


class TestUDPAdapterConfig:
    """测试UDP适配器配置"""

    def test_create_basic_config(self):
        """测试创建基础配置"""
        config = UDPAdapterConfig(
            name="UDP测试适配器",
            listen_address="0.0.0.0",
            listen_port=8888
        )

        assert config.name == "UDP测试适配器"
        assert config.listen_address == "0.0.0.0"
        assert config.listen_port == 8888
        assert config.buffer_size == 8192
        assert config.is_active is True

    def test_config_with_frame_schema(self):
        """测试包含帧格式的配置"""
        from uuid import uuid4

        schema_id = uuid4()
        config = UDPAdapterConfig(
            name="传感器UDP适配器",
            listen_address="127.0.0.1",
            listen_port=9999,
            frame_schema_id=schema_id,
            auto_parse=True,
            buffer_size=4096
        )

        assert config.frame_schema_id == schema_id
        assert config.auto_parse is True
        assert config.buffer_size == 4096

    def test_invalid_port(self):
        """测试无效端口号"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UDPAdapterConfig(
                name="测试",
                listen_port=70000  # 超过65535
            )


class TestUDPAdapter:
    """测试UDP适配器核心功能"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def adapter_config(self):
        """创建测试配置"""
        return UDPAdapterConfig(
            name="测试UDP适配器",
            listen_address="127.0.0.1",
            listen_port=0,  # 使用0让系统自动分配端口
            buffer_size=4096
        )

    @pytest.fixture
    async def adapter(self, adapter_config, eventbus):
        """创建UDP适配器实例"""
        adapter = UDPAdapter(adapter_config, eventbus)
        yield adapter
        # 清理
        if adapter.is_running:
            await adapter.stop()

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.config.name == "测试UDP适配器"
        assert adapter.is_running is False
        assert adapter.transport is None

    @pytest.mark.asyncio
    async def test_adapter_start_stop(self, adapter):
        """测试适配器启动和停止"""
        # 启动适配器
        await adapter.start()

        assert adapter.is_running is True
        assert adapter.transport is not None
        assert adapter.actual_port > 0  # 应该有实际端口号

        # 停止适配器
        await adapter.stop()

        assert adapter.is_running is False
        assert adapter.transport is None

    @pytest.mark.asyncio
    async def test_receive_udp_message(self, adapter, eventbus):
        """测试接收UDP消息"""
        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append((data, topic, source))

        # 订阅UDP接收主题
        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)

        # 启动适配器
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送测试数据
        test_data = b"Hello UDP"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(test_data, ("127.0.0.1", actual_port))
        sock.close()

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证消息
        assert len(received_messages) == 1
        message_data, topic, source = received_messages[0]

        assert topic == TopicCategory.UDP_RECEIVED
        assert source == "udp_adapter"
        assert isinstance(message_data, dict)
        assert message_data["raw_data"] == test_data
        assert message_data["source_protocol"] == ProtocolType.UDP

    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self, adapter, eventbus):
        """测试接收多个UDP消息"""
        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append(data)

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送多个消息
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(10):
            test_data = f"Message {i}".encode()
            sock.sendto(test_data, ("127.0.0.1", actual_port))
        sock.close()

        # 等待消息处理
        await asyncio.sleep(0.2)

        # 验证接收到所有消息
        assert len(received_messages) == 10
        for i in range(10):
            assert received_messages[i]["raw_data"] == f"Message {i}".encode()

    @pytest.mark.asyncio
    async def test_large_message_handling(self, adapter, eventbus):
        """测试大数据包处理"""
        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append(data)

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送大数据包（接近缓冲区大小）
        large_data = b"X" * 4000
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(large_data, ("127.0.0.1", actual_port))
        sock.close()

        await asyncio.sleep(0.1)

        assert len(received_messages) == 1
        assert len(received_messages[0]["raw_data"]) == 4000

    @pytest.mark.asyncio
    async def test_message_metadata(self, adapter, eventbus):
        """测试消息元数据完整性"""
        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append(data)

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送测试数据
        test_data = b"Metadata Test"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(test_data, ("127.0.0.1", actual_port))
        sock.close()

        await asyncio.sleep(0.1)

        assert len(received_messages) == 1
        message = received_messages[0]

        # 验证元数据
        assert "message_id" in message
        assert "timestamp" in message
        assert "source_protocol" in message
        assert "source_address" in message
        assert "source_port" in message
        assert "raw_data" in message
        assert "data_size" in message

        assert message["source_protocol"] == ProtocolType.UDP
        assert message["data_size"] == len(test_data)
        assert message["source_address"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_error_handling(self, adapter, eventbus):
        """测试错误处理"""
        # 测试重复启动
        await adapter.start()

        with pytest.raises(RuntimeError, match="already running"):
            await adapter.start()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_adapter_restart(self, adapter, eventbus):
        """测试适配器重启"""
        # 第一次启动
        await adapter.start()
        first_port = adapter.actual_port
        assert adapter.is_running is True

        # 停止
        await adapter.stop()
        assert adapter.is_running is False

        # 第二次启动
        await adapter.start()
        second_port = adapter.actual_port
        assert adapter.is_running is True
        assert second_port > 0  # 可能与第一次端口不同


class TestUDPAdapterWithFrameSchema:
    """测试UDP适配器与帧格式解析集成"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.fixture
    def frame_schema(self):
        """创建简单的帧格式定义"""
        from uuid import uuid4
        from app.schemas.frame_schema import (
            FrameSchemaResponse, FieldDefinition
        )
        from app.schemas.common import (
            FrameType, DataType, ByteOrder
        )

        schema_id = uuid4()
        return FrameSchemaResponse(
            id=schema_id,
            name="简单传感器帧",
            description="测试用帧格式",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="header",
                    data_type=DataType.UINT16,
                    offset=0,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN
                ),
                FieldDefinition(
                    name="temperature",
                    data_type=DataType.INT16,
                    offset=2,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN,
                    scale=0.1
                ),
                FieldDefinition(
                    name="humidity",
                    data_type=DataType.UINT16,
                    offset=4,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN,
                    scale=0.1
                )
            ],
            checksum_type="NONE",
            checksum_offset=None,
            checksum_length=None,
            is_published=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_auto_parse_with_frame_schema(self, frame_schema, eventbus):
        """测试自动解析帧数据"""
        import struct

        # 创建带帧解析的适配器
        config = UDPAdapterConfig(
            name="传感器适配器",
            listen_address="127.0.0.1",
            listen_port=0,
            frame_schema_id=frame_schema.id,
            auto_parse=True
        )

        adapter = UDPAdapter(config, eventbus, frame_schema=frame_schema)

        # 验证解析器已创建
        assert adapter.frame_parser is not None
        assert adapter.config.frame_schema_id == frame_schema.id
        assert adapter.config.auto_parse is True

        # 收集接收到的消息
        received_raw = []
        received_parsed = []

        def raw_handler(data, topic, source):
            received_raw.append(data)

        def parsed_handler(data, topic, source):
            received_parsed.append(data)

        # 订阅两个主题
        eventbus.subscribe(TopicCategory.UDP_RECEIVED, raw_handler)
        eventbus.subscribe(TopicCategory.DATA_PARSED, parsed_handler)

        # 启动适配器
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送测试数据: header=0xAA55, temp=25.5°C(255), humidity=60.5%(605)
        test_data = struct.pack('>HHH', 0xAA55, 255, 605) + b'\x00\x00'

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(test_data, ("127.0.0.1", actual_port))
        sock.close()

        # 等待处理
        await asyncio.sleep(0.2)

        await adapter.stop()

        # 验证收到原始数据
        assert len(received_raw) == 1
        assert received_raw[0]["raw_data"] == test_data

        # 验证收到解析后的数据
        assert len(received_parsed) == 1
        parsed_msg = received_parsed[0]

        assert "parsed_data" in parsed_msg
        parsed = parsed_msg["parsed_data"]

        # 验证解析结果
        assert parsed["header"] == 0xAA55
        assert abs(parsed["temperature"] - 25.5) < 0.01
        assert abs(parsed["humidity"] - 60.5) < 0.01

    @pytest.mark.asyncio
    async def test_parse_error_handling(self, frame_schema, eventbus):
        """测试解析错误处理"""
        import struct

        config = UDPAdapterConfig(
            name="传感器适配器",
            listen_address="127.0.0.1",
            listen_port=0,
            frame_schema_id=frame_schema.id,
            auto_parse=True
        )

        adapter = UDPAdapter(config, eventbus, frame_schema=frame_schema)

        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append(data)

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)

        await adapter.start()
        actual_port = adapter.actual_port

        # 发送长度不足的数据（应该解析失败）
        invalid_data = b'\x00\x01\x02'

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(invalid_data, ("127.0.0.1", actual_port))
        sock.close()

        await asyncio.sleep(0.1)
        await adapter.stop()

        # 验证仍然收到原始数据，但有错误标记
        assert len(received_messages) == 1
        assert "parse_error" in received_messages[0]
        assert "数据长度不足" in received_messages[0]["parse_error"]

    @pytest.mark.asyncio
    async def test_adapter_without_frame_schema(self, eventbus):
        """测试没有帧格式的适配器（只接收原始数据）"""
        config = UDPAdapterConfig(
            name="原始数据适配器",
            listen_address="127.0.0.1",
            listen_port=0,
            auto_parse=False
        )

        adapter = UDPAdapter(config, eventbus)  # 不提供frame_schema

        # 验证没有创建解析器
        assert adapter.frame_parser is None

        received_messages = []

        def message_handler(data, topic, source):
            received_messages.append(data)

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)

        await adapter.start()
        actual_port = adapter.actual_port

        test_data = b'Hello UDP'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(test_data, ("127.0.0.1", actual_port))
        sock.close()

        await asyncio.sleep(0.1)
        await adapter.stop()

        # 验证只收到原始数据
        assert len(received_messages) == 1
        assert "parsed_data" not in received_messages[0]
        assert received_messages[0]["raw_data"] == test_data


class TestUDPAdapterPerformance:
    """测试UDP适配器性能"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return get_eventbus()

    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, eventbus):
        """测试高频消息处理"""
        config = UDPAdapterConfig(
            name="性能测试适配器",
            listen_address="127.0.0.1",
            listen_port=0,
            buffer_size=8192
        )

        adapter = UDPAdapter(config, eventbus)
        received_count = [0]

        def message_handler(data, topic, source):
            received_count[0] += 1

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, message_handler)
        await adapter.start()
        actual_port = adapter.actual_port

        # 发送1000个消息
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        start_time = asyncio.get_event_loop().time()

        for i in range(1000):
            sock.sendto(f"Message {i}".encode(), ("127.0.0.1", actual_port))

        sock.close()

        # 等待处理完成
        await asyncio.sleep(1.0)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        await adapter.stop()

        # 验证性能
        assert received_count[0] >= 990  # 允许少量丢包
        throughput = received_count[0] / duration
        print(f"UDP吞吐量: {throughput:.0f} msg/s")
        assert throughput > 100  # 至少100 msg/s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])