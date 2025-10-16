"""
MQTT协议适配器实现
订阅MQTT主题并接收消息，发布到EventBus
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.frame_schema import FrameSchemaResponse
from app.core.gateway.adapters.base import BaseAdapter

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:  # pragma: no cover - 环境未安装 paho-mqtt
    mqtt = None
    MQTT_AVAILABLE = False

logger = logging.getLogger(__name__)


class MQTTAdapterConfig(BaseModel):
    """MQTT适配器配置模型"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, description="适配器名称")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    broker_host: str = Field(..., min_length=1, description="MQTT Broker地址")
    broker_port: int = Field(default=1883, ge=1, le=65535, description="MQTT Broker端口")
    topics: List[str] = Field(..., min_length=1, description="订阅的主题列表，支持通配符")
    client_id: Optional[str] = Field(None, description="客户端ID，不指定则自动生成")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    qos: int = Field(default=0, ge=0, le=2, description="QoS级别：0=最多一次，1=至少一次，2=恰好一次")
    is_active: bool = Field(default=True, description="是否激活")


class MQTTAdapter(BaseAdapter):
    """
    MQTT协议适配器

    功能：
    - 连接到MQTT Broker
    - 订阅指定主题（支持通配符）
    - 接收MQTT消息
    - 发布到EventBus
    - 支持QoS 0/1/2

    注意：
    - MQTT消息payload通常是JSON或其他结构化格式，不需要帧解析
    - 此适配器用于接收外部MQTT系统的数据
    - 与内部EventBus是独立的消息总线
    - 实际连接需要asyncio_mqtt或paho-mqtt库
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化MQTT适配器

        Args:
            config: 适配器配置字典（兼容MQTTAdapterConfig）
            eventbus: EventBus实例
            frame_schema: 兼容BaseAdapter签名，MQTT适配器无需帧格式
        """
        # 调用父类初始化（MQTT不需要frame_schema）
        super().__init__(config, eventbus, frame_schema=frame_schema)

        # 如果config是字典，转换为MQTTAdapterConfig
        if isinstance(config, dict):
            self.mqtt_config = MQTTAdapterConfig(**config)
        elif isinstance(config, MQTTAdapterConfig):
            self.mqtt_config = config
        else:
            raise TypeError("config must be dict or MQTTAdapterConfig")

        # MQTT特定属性
        self.is_connected = False
        self.client_id = self.mqtt_config.client_id or f"gateway-{uuid4()}"
        self.client: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected_event: Optional[asyncio.Event] = None
        self._disconnecting = False

        # MQTT适配器特定统计（扩展基类统计）
        self._stats["topics_subscribed"] = len(self.mqtt_config.topics)
        self._stats["connection_lost_count"] = 0

    async def start(self):
        """启动MQTT适配器"""
        if self.is_running:
            raise RuntimeError(f"MQTT适配器 '{self.mqtt_config.name}' already running")

        if not MQTT_AVAILABLE:
            raise RuntimeError("paho-mqtt 库未安装，无法启动 MQTT 适配器")

        self._loop = asyncio.get_running_loop()
        self._connected_event = asyncio.Event()
        self._disconnecting = False

        self.is_running = True
        self.is_connected = False

        client_kwargs: Dict[str, Any] = {}
        if hasattr(mqtt, "CallbackAPIVersion"):
            client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2

        self.client = mqtt.Client(client_id=self.client_id, **client_kwargs)
        if self.mqtt_config.username:
            self.client.username_pw_set(
                self.mqtt_config.username,
                self.mqtt_config.password
            )

        self.client.on_connect = self._on_connect  # type: ignore[assignment]
        self.client.on_disconnect = self._on_disconnect  # type: ignore[assignment]
        self.client.on_message = self._on_message  # type: ignore[assignment]

        logger.info(
            "MQTT适配器 '%s' 正在连接 %s:%s 订阅 %s",
            self.mqtt_config.name,
            self.mqtt_config.broker_host,
            self.mqtt_config.broker_port,
            ", ".join(self.mqtt_config.topics),
        )

        try:
            self.client.loop_start()
            self.client.connect_async(
                self.mqtt_config.broker_host,
                self.mqtt_config.broker_port,
                keepalive=60,
            )

            try:
                await asyncio.wait_for(self._connected_event.wait(), timeout=15.0)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("MQTT 连接超时") from exc

            if not self.is_connected:
                raise RuntimeError("MQTT 连接失败")

            logger.info(
                "MQTT适配器 '%s' 已连接，客户端ID: %s",
                self.mqtt_config.name,
                self.client_id,
            )
        except Exception:
            await self.stop()
            raise

    async def stop(self):
        """停止MQTT适配器"""
        if not self.is_running:
            return

        self._disconnecting = True
        self.is_running = False
        self.is_connected = False

        if self.client:
            try:
                self.client.loop_stop()
            except Exception:  # pragma: no cover
                pass
            try:
                self.client.disconnect()
            except Exception:  # pragma: no cover
                pass
            self.client = None

        if self._connected_event:
            self._connected_event.clear()
        self._connected_event = None
        self._loop = None
        self._disconnecting = False

        logger.info("MQTT适配器 '%s' 已停止", self.mqtt_config.name)

    async def restart(self):
        """重启MQTT适配器"""
        await self.stop()
        await self.start()

    async def receive_message(
        self,
        topic: str,
        payload: bytes,
        qos: int = 0
    ):
        """
        接收MQTT消息

        Args:
            topic: 消息主题
            payload: 消息内容（字节流）
            qos: QoS级别
        """
        try:
            raw_data = bytes(payload)

            raw_text: Optional[str] = None
            parsed_value: Optional[Any] = None

            try:
                raw_text = raw_data.decode("utf-8")
                try:
                    parsed_value = json.loads(raw_text)
                except json.JSONDecodeError:
                    parsed_value = raw_text
            except UnicodeDecodeError:
                raw_text = None

            # 更新统计
            self._stats["messages_received"] += 1
            self._stats["bytes_received"] += len(raw_data)

            message_data = {
                "message_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_protocol": ProtocolType.MQTT,
                "data_source_id": self.mqtt_config.data_source_id,
                "topic": topic,
                "payload": raw_data,
                "payload_size": len(raw_data),
                "qos": qos,
                "adapter_name": self.mqtt_config.name,
                "broker": f"{self.mqtt_config.broker_host}:{self.mqtt_config.broker_port}",
                "raw_data": raw_data,
                "raw_text": raw_text,
                "parsed_data": parsed_value,
            }

            self.eventbus.publish(
                topic=TopicCategory.MQTT_RECEIVED,
                data=message_data,
                source="mqtt_adapter"
            )

            logger.info(
                "MQTT接收消息: topic=%s, size=%s bytes, qos=%s",
                topic,
                len(raw_data),
                qos,
            )

        except Exception as e:
            logger.error("处理MQTT消息时出错: %s", e, exc_info=True)
            self._stats["errors"] += 1

    def get_subscribed_topics(self) -> List[str]:
        """
        获取订阅的主题列表

        Returns:
            主题列表
        """
        return self.mqtt_config.topics

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "name": self.mqtt_config.name,
            "is_running": self.is_running,
            "is_connected": self.is_connected,
            "broker_host": self.mqtt_config.broker_host,
            "broker_port": self.mqtt_config.broker_port,
            "client_id": self.client_id,
            "topics": self.mqtt_config.topics,
            "qos": self.mqtt_config.qos,
            **self._stats  # 包含基类统计信息
        }

    # ========== MQTT 回调 ==========

    def _on_connect(self, client, _userdata, _flags, rc, properties=None):  # type: ignore[no-untyped-def]
        if rc == 0:
            self.is_connected = True
            for topic in self.mqtt_config.topics:
                client.subscribe(topic, qos=self.mqtt_config.qos)
                logger.info("MQTT适配器 '%s' 订阅主题: %s", self.mqtt_config.name, topic)
        else:
            self.is_connected = False
            logger.error("MQTT适配器 '%s' 连接失败，返回码: %s", self.mqtt_config.name, rc)

        if self._connected_event and not self._connected_event.is_set():
            try:
                self._loop.call_soon_threadsafe(self._connected_event.set)  # type: ignore[arg-type]
            except RuntimeError:  # pragma: no cover - loop已关闭
                pass

    def _on_disconnect(self, _client, _userdata, rc, properties=None):  # type: ignore[no-untyped-def]
        self.is_connected = False
        if not self._disconnecting:
            self._stats["connection_lost_count"] += 1
            logger.warning("MQTT适配器 '%s' 意外断开 (rc=%s)", self.mqtt_config.name, rc)
        else:
            logger.info("MQTT适配器 '%s' 连接已关闭", self.mqtt_config.name)

    def _on_message(self, _client, _userdata, msg):  # type: ignore[no-untyped-def]
        if not self.is_running or not self._loop:
            return

        payload = msg.payload or b""
        if not isinstance(payload, (bytes, bytearray)):
            payload = bytes(payload)

        try:
            asyncio.run_coroutine_threadsafe(
                self.receive_message(msg.topic, bytes(payload), msg.qos),
                self._loop,
            )
        except Exception as exc:  # pragma: no cover - 线程调度异常
            logger.error("MQTT适配器 '%s' 处理消息失败: %s", self.mqtt_config.name, exc, exc_info=True)
