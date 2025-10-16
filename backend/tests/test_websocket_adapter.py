"""
WebSocket协议适配器测试
"""
import pytest
import asyncio
from uuid import uuid4

from app.core.eventbus import get_eventbus, reset_eventbus, TopicCategory
from app.core.gateway.adapters.websocket_adapter import WebSocketAdapter, WebSocketAdapterConfig
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
def ws_config():
    """WebSocket适配器配置"""
    return {
        "name": "测试WebSocket适配器",
        "endpoint": "/ws/data",
        "is_active": True
    }


class TestWebSocketAdapterConfig:
    """测试WebSocket适配器配置"""

    def test_config_with_defaults(self):
        """测试默认配置"""
        config = WebSocketAdapterConfig(
            name="测试",
            endpoint="/ws/data"
        )

        assert config.name == "测试"
        assert config.endpoint == "/ws/data"
        assert config.is_active is True
        assert config.max_connections == 100

    def test_config_custom_max_connections(self):
        """测试自定义最大连接数"""
        config = WebSocketAdapterConfig(
            name="测试",
            endpoint="/ws/data",
            max_connections=500
        )

        assert config.max_connections == 500


class TestWebSocketAdapter:
    """测试WebSocket适配器"""

    def test_init_with_dict(self, eventbus, ws_config):
        """测试用字典初始化"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        assert adapter.ws_config.name == "测试WebSocket适配器"
        assert adapter.ws_config.endpoint == "/ws/data"
        assert adapter.eventbus is eventbus
        assert adapter.is_running is False

    def test_init_with_config_object(self, eventbus):
        """测试用配置对象初始化"""
        config = WebSocketAdapterConfig(
            name="测试",
            endpoint="/ws/data"
        )

        adapter = WebSocketAdapter(
            config=config,
            eventbus=eventbus
        )

        assert adapter.ws_config.name == "测试"

    @pytest.mark.asyncio
    async def test_receive_message_publishes_event(self, eventbus, ws_config):
        """测试接收消息发布事件"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        # 订阅事件
        received_events = []

        def on_ws_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.WEBSOCKET_RECEIVED, on_ws_received)

        # 模拟接收WebSocket消息（JSON文本）
        connection_id = str(uuid4())
        test_message = {
            "type": "sensor_data",
            "temperature": 25.5,
            "humidity": 60.0
        }

        await adapter.receive_message(
            connection_id=connection_id,
            message=test_message,
            client_address="192.168.1.100"
        )

        # 验证事件发布
        assert len(received_events) == 1
        event = received_events[0]

        assert event["source_protocol"] == ProtocolType.WEBSOCKET
        assert event["connection_id"] == connection_id
        assert event["client_address"] == "192.168.1.100"
        assert event["adapter_name"] == "测试WebSocket适配器"
        assert event["message"] == test_message
        assert "message_id" in event
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_receive_text_message(self, eventbus, ws_config):
        """测试接收文本消息"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        received_events = []

        def on_ws_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.WEBSOCKET_RECEIVED, on_ws_received)

        connection_id = str(uuid4())
        await adapter.receive_message(
            connection_id=connection_id,
            message="Hello WebSocket!",
            client_address="192.168.1.100"
        )

        assert len(received_events) == 1
        assert received_events[0]["message"] == "Hello WebSocket!"

    @pytest.mark.asyncio
    async def test_receive_binary_message(self, eventbus, ws_config):
        """测试接收二进制消息"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        received_events = []

        def on_ws_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.WEBSOCKET_RECEIVED, on_ws_received)

        connection_id = str(uuid4())
        binary_data = b'\x01\x02\x03\x04'

        await adapter.receive_message(
            connection_id=connection_id,
            message=binary_data,
            client_address="192.168.1.100"
        )

        assert len(received_events) == 1
        assert received_events[0]["message"] == binary_data

    @pytest.mark.asyncio
    async def test_start_stop(self, eventbus, ws_config):
        """测试启动和停止"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        assert adapter.is_running is False

        await adapter.start()
        assert adapter.is_running is True

        await adapter.stop()
        assert adapter.is_running is False

    @pytest.mark.asyncio
    async def test_restart(self, eventbus, ws_config):
        """测试重启"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        await adapter.start()
        assert adapter.is_running is True

        await adapter.restart()
        assert adapter.is_running is True

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_connection_management(self, eventbus, ws_config):
        """测试连接管理"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加连接
        conn_id_1 = "conn-1"
        conn_id_2 = "conn-2"

        await adapter.add_connection(conn_id_1, "192.168.1.100")
        await adapter.add_connection(conn_id_2, "192.168.1.101")

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
        config = WebSocketAdapterConfig(
            name="测试",
            endpoint="/ws/data",
            max_connections=2
        )

        adapter = WebSocketAdapter(
            config=config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加连接直到达到限制
        await adapter.add_connection("conn-1", "192.168.1.100")
        await adapter.add_connection("conn-2", "192.168.1.101")

        # 尝试添加第3个连接应该失败
        with pytest.raises(RuntimeError, match="Maximum connections reached"):
            await adapter.add_connection("conn-3", "192.168.1.102")

        await adapter.stop()

    def test_get_stats(self, eventbus, ws_config):
        """测试获取统计信息"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        stats = adapter.get_stats()

        assert stats["name"] == "测试WebSocket适配器"
        assert stats["is_running"] is False
        assert stats["endpoint"] == "/ws/data"
        assert stats["max_connections"] == 100
        assert stats["active_connections"] == 0
        assert "messages_received" in stats
        assert "errors" in stats

    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self, eventbus, ws_config):
        """测试接收多个消息"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        await adapter.start()

        connection_id = "conn-1"
        await adapter.add_connection(connection_id, "192.168.1.100")

        # 发送多个消息
        for i in range(5):
            await adapter.receive_message(
                connection_id=connection_id,
                message={"index": i},
                client_address="192.168.1.100"
            )

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, eventbus, ws_config):
        """测试并发消息"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加多个连接
        for i in range(5):
            await adapter.add_connection(f"conn-{i}", f"192.168.1.{100+i}")

        # 并发发送消息
        tasks = []
        for i in range(5):
            task = adapter.receive_message(
                connection_id=f"conn-{i}",
                message={"index": i},
                client_address=f"192.168.1.{100+i}"
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5
        assert stats["active_connections"] == 5

        await adapter.stop()

    def test_get_endpoint_path(self, eventbus, ws_config):
        """测试获取端点路径"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        assert adapter.get_endpoint_path() == "/ws/data"

    @pytest.mark.asyncio
    async def test_broadcast_capability(self, eventbus, ws_config):
        """测试广播能力（获取所有连接）"""
        adapter = WebSocketAdapter(
            config=ws_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 添加多个连接
        await adapter.add_connection("conn-1", "192.168.1.100")
        await adapter.add_connection("conn-2", "192.168.1.101")
        await adapter.add_connection("conn-3", "192.168.1.102")

        connections = adapter.get_all_connections()
        assert len(connections) == 3
        assert "conn-1" in connections
        assert "conn-2" in connections
        assert "conn-3" in connections

        await adapter.stop()
