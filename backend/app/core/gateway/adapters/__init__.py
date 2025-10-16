# 协议适配器模块

from .base import BaseAdapter
from .factory import AdapterFactory
from .udp_adapter import UDPAdapter, UDPAdapterConfig
from .http_adapter import HTTPAdapter, HTTPAdapterConfig
from .websocket_adapter import WebSocketAdapter, WebSocketAdapterConfig
from .tcp_adapter import TCPAdapter, TCPAdapterConfig
from .mqtt_adapter import MQTTAdapter, MQTTAdapterConfig

# 注册适配器到工厂
from app.schemas.common import ProtocolType
AdapterFactory.register(ProtocolType.UDP, UDPAdapter)
AdapterFactory.register(ProtocolType.HTTP, HTTPAdapter)
AdapterFactory.register(ProtocolType.WEBSOCKET, WebSocketAdapter)
AdapterFactory.register(ProtocolType.TCP, TCPAdapter)
AdapterFactory.register(ProtocolType.MQTT, MQTTAdapter)

__all__ = [
    "BaseAdapter",
    "AdapterFactory",
    "UDPAdapter",
    "UDPAdapterConfig",
    "HTTPAdapter",
    "HTTPAdapterConfig",
    "WebSocketAdapter",
    "WebSocketAdapterConfig",
    "TCPAdapter",
    "TCPAdapterConfig",
    "MQTTAdapter",
    "MQTTAdapterConfig",
]