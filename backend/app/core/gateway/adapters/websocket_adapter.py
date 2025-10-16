"""
WebSocket协议适配器实现
管理WebSocket连接并接收消息，发布到EventBus
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.frame_schema import FrameSchemaResponse
from app.core.gateway.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class WebSocketAdapterConfig(BaseModel):
    """WebSocket适配器配置模型"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, description="适配器名称")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    endpoint: str = Field(..., min_length=1, description="WebSocket端点路径，如/ws/data")
    max_connections: int = Field(default=100, ge=1, description="最大连接数")
    is_active: bool = Field(default=True, description="是否激活")


class WebSocketAdapter(BaseAdapter):
    """
    WebSocket协议适配器

    功能：
    - 管理WebSocket连接
    - 接收WebSocket消息（文本/二进制）
    - 发布到EventBus
    - 支持连接状态监控

    注意：
    - WebSocket通常传输结构化数据（JSON），不需要帧格式解析
    - 连接管理（accept/close）由FastAPI WebSocket路由处理
    - 此适配器仅负责消息接收和EventBus发布
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化WebSocket适配器

        Args:
            config: 适配器配置字典（兼容WebSocketAdapterConfig）
            eventbus: EventBus实例
            frame_schema: 兼容BaseAdapter签名，WebSocket适配器无需帧格式
        """
        # 调用父类初始化（WebSocket不需要frame_schema）
        super().__init__(config, eventbus, frame_schema=frame_schema)

        # 如果config是字典，转换为WebSocketAdapterConfig
        if isinstance(config, dict):
            self.ws_config = WebSocketAdapterConfig(**config)
        elif isinstance(config, WebSocketAdapterConfig):
            self.ws_config = config
        else:
            raise TypeError("config must be dict or WebSocketAdapterConfig")

        # WebSocket特定属性
        self.connections: Dict[str, Dict[str, Any]] = {}  # connection_id -> {client_address, connected_at}

        # WebSocket适配器特定统计（扩展基类统计）
        self._stats["messages_sent"] = 0
        self._stats["active_connections"] = 0
        self._stats["total_connections"] = 0

    async def start(self):
        """启动WebSocket适配器"""
        if self.is_running:
            raise RuntimeError(f"WebSocket适配器 '{self.ws_config.name}' already running")

        self.is_running = True

        logger.info(
            f"WebSocket适配器 '{self.ws_config.name}' 启动，"
            f"端点: {self.ws_config.endpoint}, 最大连接数: {self.ws_config.max_connections}"
        )

    async def stop(self):
        """停止WebSocket适配器"""
        if not self.is_running:
            return

        # 清理所有连接
        self.connections.clear()
        self._stats["active_connections"] = 0

        self.is_running = False

        logger.info(f"WebSocket适配器 '{self.ws_config.name}' 已停止")

    async def restart(self):
        """重启WebSocket适配器"""
        await self.stop()
        await self.start()

    async def add_connection(self, connection_id: str, client_address: str):
        """
        添加WebSocket连接

        Args:
            connection_id: 连接ID（通常是UUID）
            client_address: 客户端地址

        Raises:
            RuntimeError: 如果达到最大连接数
        """
        if len(self.connections) >= self.ws_config.max_connections:
            raise RuntimeError(
                f"Maximum connections reached ({self.ws_config.max_connections})"
            )

        self.connections[connection_id] = {
            "client_address": client_address,
            "connected_at": datetime.now().isoformat()
        }

        self._stats["active_connections"] = len(self.connections)
        self._stats["total_connections"] += 1

        logger.info(
            f"WebSocket连接已建立: {connection_id} from {client_address} "
            f"(当前连接数: {len(self.connections)})"
        )

    async def remove_connection(self, connection_id: str):
        """
        移除WebSocket连接

        Args:
            connection_id: 连接ID
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            self._stats["active_connections"] = len(self.connections)

            logger.info(
                f"WebSocket连接已断开: {connection_id} "
                f"(当前连接数: {len(self.connections)})"
            )

    async def receive_message(
        self,
        connection_id: str,
        message: Any,
        client_address: str
    ):
        """
        接收WebSocket消息

        Args:
            connection_id: 连接ID
            message: 消息内容（可以是dict、str、bytes等）
            client_address: 客户端地址
        """
        try:
            # 更新统计
            self._stats["messages_received"] += 1

            # 构建消息数据
            message_data = {
                "message_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_protocol": ProtocolType.WEBSOCKET,
                "data_source_id": self.ws_config.data_source_id,
                "connection_id": connection_id,
                "client_address": client_address,
                "message": message,
                "adapter_name": self.ws_config.name,
                "endpoint": self.ws_config.endpoint
            }

            # 发布到EventBus
            self.eventbus.publish(
                topic=TopicCategory.WEBSOCKET_RECEIVED,
                data=message_data,
                source="websocket_adapter"
            )

            logger.info(
                f"WebSocket接收消息: endpoint={self.ws_config.endpoint}, "
                f"connection={connection_id}"
            )

        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {e}", exc_info=True)
            self._stats["errors"] += 1

    def get_all_connections(self) -> List[str]:
        """
        获取所有活跃连接ID

        Returns:
            连接ID列表
        """
        return list(self.connections.keys())

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        获取连接信息

        Args:
            connection_id: 连接ID

        Returns:
            连接信息字典，如果不存在返回None
        """
        return self.connections.get(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "name": self.ws_config.name,
            "is_running": self.is_running,
            "endpoint": self.ws_config.endpoint,
            "max_connections": self.ws_config.max_connections,
            "active_connections": len(self.connections),
            **self._stats  # 包含基类统计信息
        }

    def get_endpoint_path(self) -> str:
        """获取WebSocket端点路径"""
        return self.ws_config.endpoint
