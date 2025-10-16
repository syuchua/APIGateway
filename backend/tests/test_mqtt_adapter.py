"""
MQTT协议适配器测试
"""
import pytest
import asyncio
from uuid import uuid4

from app.core.eventbus import get_eventbus, reset_eventbus, TopicCategory
from app.core.gateway.adapters.mqtt_adapter import MQTTAdapter, MQTTAdapterConfig
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
def mqtt_config():
    """MQTT适配器配置"""
    return {
        "name": "测试MQTT适配器",
        "broker_host": "localhost",
        "broker_port": 1883,
        "topics": ["sensor/+/data", "device/#"],
        "is_active": True
    }


class TestMQTTAdapterConfig:
    """测试MQTT适配器配置"""

    def test_config_with_defaults(self):
        """测试默认配置"""
        config = MQTTAdapterConfig(
            name="测试",
            broker_host="localhost",
            topics=["test/topic"]
        )

        assert config.name == "测试"
        assert config.broker_host == "localhost"
        assert config.broker_port == 1883
        assert config.topics == ["test/topic"]
        assert config.client_id is None  # 自动生成
        assert config.username is None
        assert config.password is None
        assert config.qos == 0
        assert config.is_active is True

    def test_config_with_auth(self):
        """测试带认证配置"""
        config = MQTTAdapterConfig(
            name="测试",
            broker_host="localhost",
            topics=["test/topic"],
            username="admin",
            password="secret",
            qos=2
        )

        assert config.username == "admin"
        assert config.password == "secret"
        assert config.qos == 2

    def test_config_custom_client_id(self):
        """测试自定义客户端ID"""
        config = MQTTAdapterConfig(
            name="测试",
            broker_host="localhost",
            topics=["test/topic"],
            client_id="my-client-123"
        )

        assert config.client_id == "my-client-123"


class TestMQTTAdapter:
    """测试MQTT适配器"""

    def test_init_with_dict(self, eventbus, mqtt_config):
        """测试用字典初始化"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        assert adapter.mqtt_config.name == "测试MQTT适配器"
        assert adapter.mqtt_config.broker_host == "localhost"
        assert adapter.mqtt_config.broker_port == 1883
        assert adapter.mqtt_config.topics == ["sensor/+/data", "device/#"]
        assert adapter.eventbus is eventbus
        assert adapter.is_running is False

    def test_init_with_config_object(self, eventbus):
        """测试用配置对象初始化"""
        config = MQTTAdapterConfig(
            name="测试",
            broker_host="localhost",
            topics=["test/topic"]
        )

        adapter = MQTTAdapter(
            config=config,
            eventbus=eventbus
        )

        assert adapter.mqtt_config.name == "测试"

    @pytest.mark.asyncio
    async def test_receive_message_publishes_event(self, eventbus, mqtt_config):
        """测试接收消息发布事件"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        # 订阅事件
        received_events = []

        def on_mqtt_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.MQTT_RECEIVED, on_mqtt_received)

        # 模拟接收MQTT消息
        test_payload = b'{"temperature": 25.5, "humidity": 60.0}'

        await adapter.receive_message(
            topic="sensor/room1/data",
            payload=test_payload,
            qos=0
        )

        # 验证事件发布
        assert len(received_events) == 1
        event = received_events[0]

        assert event["source_protocol"] == ProtocolType.MQTT
        assert event["topic"] == "sensor/room1/data"
        assert event["adapter_name"] == "测试MQTT适配器"
        assert event["payload"] == test_payload
        assert event["qos"] == 0
        assert "message_id" in event
        assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_receive_json_message(self, eventbus, mqtt_config):
        """测试接收JSON消息"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        received_events = []

        def on_mqtt_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.MQTT_RECEIVED, on_mqtt_received)

        # JSON格式的payload
        import json
        payload = json.dumps({"temp": 25.5}).encode()

        await adapter.receive_message(
            topic="sensor/data",
            payload=payload,
            qos=1
        )

        assert len(received_events) == 1
        assert received_events[0]["payload"] == payload

    @pytest.mark.asyncio
    async def test_receive_binary_message(self, eventbus, mqtt_config):
        """测试接收二进制消息"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        received_events = []

        def on_mqtt_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.MQTT_RECEIVED, on_mqtt_received)

        binary_payload = b'\x01\x02\x03\x04'

        await adapter.receive_message(
            topic="device/binary",
            payload=binary_payload,
            qos=2
        )

        assert len(received_events) == 1
        assert received_events[0]["payload"] == binary_payload
        assert received_events[0]["qos"] == 2

    @pytest.mark.asyncio
    async def test_start_stop(self, eventbus, mqtt_config):
        """测试启动和停止"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        assert adapter.is_running is False
        assert adapter.is_connected is False

        await adapter.start()
        assert adapter.is_running is True
        # 注意：实际连接需要MQTT broker，测试中不会真实连接

        await adapter.stop()
        assert adapter.is_running is False
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_restart(self, eventbus, mqtt_config):
        """测试重启"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        await adapter.start()
        assert adapter.is_running is True

        await adapter.restart()
        assert adapter.is_running is True

        await adapter.stop()

    def test_get_stats(self, eventbus, mqtt_config):
        """测试获取统计信息"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        stats = adapter.get_stats()

        assert stats["name"] == "测试MQTT适配器"
        assert stats["is_running"] is False
        assert stats["is_connected"] is False
        assert stats["broker_host"] == "localhost"
        assert stats["broker_port"] == 1883
        assert stats["topics"] == ["sensor/+/data", "device/#"]
        assert stats["qos"] == 0
        assert "messages_received" in stats
        assert "errors" in stats

    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self, eventbus, mqtt_config):
        """测试接收多个消息"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 发送多个消息
        for i in range(5):
            await adapter.receive_message(
                topic=f"sensor/room{i}/data",
                payload=f'{{"index": {i}}}'.encode(),
                qos=0
            )

        stats = adapter.get_stats()
        assert stats["messages_received"] == 5

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, eventbus, mqtt_config):
        """测试并发消息"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        await adapter.start()

        # 并发发送消息
        tasks = []
        for i in range(10):
            task = adapter.receive_message(
                topic=f"test/topic{i}",
                payload=f"message-{i}".encode(),
                qos=0
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        stats = adapter.get_stats()
        assert stats["messages_received"] == 10

        await adapter.stop()

    def test_get_subscribed_topics(self, eventbus, mqtt_config):
        """测试获取订阅主题"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        topics = adapter.get_subscribed_topics()
        assert topics == ["sensor/+/data", "device/#"]

    @pytest.mark.asyncio
    async def test_empty_payload(self, eventbus, mqtt_config):
        """测试空payload"""
        adapter = MQTTAdapter(
            config=mqtt_config,
            eventbus=eventbus
        )

        received_events = []

        def on_mqtt_received(data, topic, source):
            received_events.append(data)

        eventbus.subscribe(TopicCategory.MQTT_RECEIVED, on_mqtt_received)

        await adapter.receive_message(
            topic="test/empty",
            payload=b'',
            qos=0
        )

        assert len(received_events) == 1
        assert received_events[0]["payload"] == b''
        assert received_events[0]["payload_size"] == 0
