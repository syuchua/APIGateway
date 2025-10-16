# 转发器模块
import logging

from app.schemas.common import ProtocolType

from .base import BaseForwarder
from .factory import ForwarderFactory
from .forwarder_manager import ForwarderManager
from .http_forwarder import HTTPForwarder
from .mqtt_forwarder import MQTTForwarder
from .tcp_forwarder import TCPForwarder
from .udp_forwarder import UDPForwarder

logger = logging.getLogger(__name__)

# 注册已实现的转发器
ForwarderFactory.register(ProtocolType.HTTP, HTTPForwarder)
ForwarderFactory.register(ProtocolType.UDP, UDPForwarder)
ForwarderFactory.register(ProtocolType.TCP, TCPForwarder)
ForwarderFactory.register(ProtocolType.MQTT, MQTTForwarder)

try:
    from .websocket_forwarder import WebSocketForwarder
except ImportError as exc:  # pragma: no cover - 可选依赖
    logger.warning("WebSocketForwarder 未启用（缺少 websockets 依赖）: %s", exc)
else:
    ForwarderFactory.register(ProtocolType.WEBSOCKET, WebSocketForwarder)

__all__ = [
    "BaseForwarder",
    "ForwarderFactory",
    "ForwarderManager",
    "HTTPForwarder",
    "MQTTForwarder",
    "TCPForwarder",
    "UDPForwarder",
]
