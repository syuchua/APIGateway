"""
TCP协议适配器测试
"""
import pytest
import asyncio
from uuid import uuid4

from app.core.eventbus import get_eventbus, reset_eventbus, TopicCategory
from app.core.gateway.adapters.tcp_adapter import TCPAdapter, TCPAdapterConfig
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
def tcp_config():
    """TCP适配器配置"""
    return {
        "name": "测试TCP适配器",
        "listen_address": "0.0.0.0",
        "listen_port": 9000,
        "is_active": True
    }


class TestTCPAdapterConfig:
    """测试TCP适配器配置"""

    def test_config_with_defaults(self):
        """测试默认配置"""
        config = TCPAdapterConfig(
            name="测试",
            listen_port=9000
        )

        assert config.name == "测试"
        assert config.listen_address == "0.0.0.0"
        assert config.listen_port == 9000
        assert config.is_active is True
        assert config.max_connections == 100
        assert config.buffer_size == 8192

    def test_config_custom_values(self):
        """测试自定义配置"""
        config = TCPAdapterConfig(
            name="测试",
            listen_address="127.0.0.1",
            listen_port=9001,
            max_connections=50,
            buffer_size=4096
        )

        assert config.listen_address == "127.0.0.1"
        assert config.listen_port == 9001
        assert config.max_connections == 50
        assert config.buffer_size == 4096

    def test_config_with_frame_schema(self):
        """测试带帧格式配置"""
        frame_schema_id = uuid4()
        config = TCPAdapterConfig(
            name="测试",
            listen_port=9000,
            frame_schema_id=frame_schema_id,
            auto_parse=True
        )

        assert config.frame_schema_id == frame_schema_id
        assert config.auto_parse is True


class TestTCPAdapter:
    """测试TCP适配器"""

    def test_init_with_dict(self, eventbus, tcp_config):
        """测试用字典初始化"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        assert adapter.tcp_config.name == "测试TCP适配器"
        assert adapter.tcp_config.listen_address == "0.0.0.0"
        assert adapter.tcp_config.listen_port == 9000
        assert adapter.eventbus is eventbus
        assert adapter.is_running is False

    def test_init_with_config_object(self, eventbus):
        """测试用配置对象初始化"""
        config = TCPAdapterConfig(
            name="测试",
            listen_port=9000
        )

        adapter = TCPAdapter(
            config=config,
            eventbus=eventbus
        )

        assert adapter.tcp_config.name == "测试"

    @pytest.mark.asyncio
    async def test_receive_data_publishes_event(self, eventbus, tcp_config):
        """测试接收数据发布事件"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        # 订阅事件
        received_events = []

        def on_tcp_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.TCP_RECEIVED, on_tcp_received)

        # 模拟接收TCP数据
        connection_id = str(uuid4())
        test_data = b'\x01\x02\x03\x04\x05'

        await adapter.receive_data(
            connection_id=connection_id,
            data=test_data,
            client_address="192.168.1.100",
            client_port=12345
        )

        # 验证事件发布
        assert len(received_events) == 1
        event = received_events[0]

        assert event["source_protocol"] == ProtocolType.TCP
        assert event["connection_id"] == connection_id
        assert event["client_address"] == "192.168.1.100"
        assert event["client_port"] == 12345
        assert event["adapter_name"] == "测试TCP适配器"
        assert event["raw_data"] == test_data
        assert event["data_size"] == 5
        assert "message_id" in event
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_receive_data_with_parsing(self, eventbus):
        """测试接收数据并自动解析"""
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

        config = TCPAdapterConfig(
            name="测试解析",
            listen_port=9000,
            auto_parse=True
        )

        adapter = TCPAdapter(
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

        connection_id = str(uuid4())
        await adapter.receive_data(
            connection_id=connection_id,
            data=raw_bytes,
            client_address="192.168.1.100",
            client_port=12345
        )

        # 验证解析事件
        assert len(parsed_events) == 1
        parsed_event = parsed_events[0]

        assert "parsed_data" in parsed_event
        assert parsed_event["parsed_data"]["temperature"] == pytest.approx(25.5, rel=0.01)
        assert parsed_event["parsed_data"]["humidity"] == pytest.approx(60.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_start_stop(self, eventbus, tcp_config):
        """测试启动和停止"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        assert adapter.is_running is False
        assert adapter.actual_port == 0

        await adapter.start()
        assert adapter.is_running is True
        # 实际端口应该被设置（测试中可能是0因为没有真实监听）

        await adapter.stop()
        assert adapter.is_running is False
        assert adapter.actual_port == 0

    @pytest.mark.asyncio
    async def test_restart(self, eventbus, tcp_config):
        """测试重启"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        await adapter.start()
        assert adapter.is_running is True

        await adapter.restart()
        assert adapter.is_running is True

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_connection_management(self, eventbus, tcp_config):
        """测试连接管理"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加连接
        conn_id_1 = "conn-1"
        conn_id_2 = "conn-2"

        await adapter.add_connection(conn_id_1, "192.168.1.100", 12345)
        await adapter.add_connection(conn_id_2, "192.168.1.101", 12346)

        stats = adapter.get_stats()
        assert stats["active_connections"] == 2

        # 移除连接
        await adapter.remove_connection(conn_id_1)

        stats = adapter.get_stats()
        assert stats["active_connections"] == 1

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_max_connections_limit(self, eventbus):
        """测试最大连接数限制"""
        config = TCPAdapterConfig(
            name="测试",
            listen_port=9000,
            max_connections=2
        )

        adapter = TCPAdapter(
            config=config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加连接直到达到限制
        await adapter.add_connection("conn-1", "192.168.1.100", 12345)
        await adapter.add_connection("conn-2", "192.168.1.101", 12346)

        # 尝试添加第3个连接应该失败
        with pytest.raises(RuntimeError, match="Maximum connections reached"):
            await adapter.add_connection("conn-3", "192.168.1.102", 12347)

        await adapter.stop()

    def test_get_stats(self, eventbus, tcp_config):
        """测试获取统计信息"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        stats = adapter.get_stats()

        assert stats["name"] == "测试TCP适配器"
        assert stats["is_running"] is False
        assert stats["listen_address"] == "0.0.0.0"
        assert stats["listen_port"] == 9000
        assert stats["actual_port"] == 0
        assert stats["buffer_size"] == 8192
        assert stats["max_connections"] == 100
        assert stats["active_connections"] == 0
        assert stats["auto_parse"] is False
        assert stats["has_frame_parser"] is False

    @pytest.mark.asyncio
    async def test_receive_multiple_data(self, eventbus, tcp_config):
        """测试接收多个数据包"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        await adapter.start()

        connection_id = "conn-1"
        await adapter.add_connection(connection_id, "192.168.1.100", 12345)

        # 发送多个数据包
        for i in range(5):
            await adapter.receive_data(
                connection_id=connection_id,
                data=bytes([i]),
                client_address="192.168.1.100",
                client_port=12345
            )

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_concurrent_data(self, eventbus, tcp_config):
        """测试并发数据"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加多个连接
        for i in range(5):
            await adapter.add_connection(f"conn-{i}", f"192.168.1.{100+i}", 12345+i)

        # 并发发送数据
        tasks = []
        for i in range(5):
            task = adapter.receive_data(
                connection_id=f"conn-{i}",
                data=bytes([i]),
                client_address=f"192.168.1.{100+i}",
                client_port=12345+i
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5
        assert stats["active_connections"] == 5

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_get_all_connections(self, eventbus, tcp_config):
        """测试获取所有连接"""
        adapter = TCPAdapter(
            config=tcp_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加多个连接
        await adapter.add_connection("conn-1", "192.168.1.100", 12345)
        await adapter.add_connection("conn-2", "192.168.1.101", 12346)
        await adapter.add_connection("conn-3", "192.168.1.102", 12347)

        connections = adapter.get_all_connections()
        assert len(connections) == 3
        assert "conn-1" in connections
        assert "conn-2" in connections
        assert "conn-3" in connections

        await adapter.stop()
