"""
TCP协议适配器实现
管理TCP连接并接收数据流，发布到EventBus
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.frame_schema import FrameSchemaResponse
from app.core.gateway.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class TCPAdapterConfig(BaseModel):
    """TCP适配器配置模型"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, description="适配器名称")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    listen_address: str = Field(default="0.0.0.0", description="监听地址")
    listen_port: int = Field(..., ge=0, le=65535, description="监听端口，0表示自动分配")
    buffer_size: int = Field(default=8192, ge=512, description="接收缓冲区大小")
    max_connections: int = Field(default=100, ge=1, description="最大连接数")
    frame_schema_id: Optional[UUID] = Field(None, description="帧格式ID")
    auto_parse: bool = Field(default=False, description="是否自动解析数据帧")
    is_active: bool = Field(default=True, description="是否激活")


class TCPAdapter(BaseAdapter):
    """
    TCP协议适配器

    功能：
    - 管理TCP长连接
    - 接收TCP数据流
    - 解析数据帧（可选）
    - 发布到EventBus
    - 支持高并发连接

    注意：
    - TCP是流式协议，如果传输自定义二进制协议，可以配置帧格式解析
    - 如果应用层使用HTTP、JSON等结构化协议，则不需要帧解析
    - 连接管理（accept/close）需要与asyncio TCP Server集成
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化TCP适配器

        Args:
            config: 适配器配置字典（兼容TCPAdapterConfig）
            eventbus: EventBus实例
            frame_schema: 帧格式定义（可选）
        """
        # 调用父类初始化
        super().__init__(config, eventbus, frame_schema)

        # 如果config是字典，转换为TCPAdapterConfig
        if isinstance(config, dict):
            self.tcp_config = TCPAdapterConfig(**config)
        elif isinstance(config, TCPAdapterConfig):
            self.tcp_config = config
        else:
            raise TypeError("config must be dict or TCPAdapterConfig")

        # TCP特定属性
        self.connections: Dict[str, Dict[str, Any]] = {}  # connection_id -> {client_address, client_port, connected_at}
        self.actual_port = 0  # 实际监听的端口
        self.frame_parser = None

        # TCP适配器特定统计（扩展基类统计）
        self._stats["active_connections"] = 0
        self._stats["total_connections"] = 0

        # 如果提供了帧格式定义，创建解析器
        if frame_schema:
            from app.core.gateway.frame.parser import FrameParser
            self.frame_parser = FrameParser(frame_schema)

    async def start(self):
        """启动TCP适配器"""
        if self.is_running:
            raise RuntimeError(f"TCP适配器 '{self.tcp_config.name}' already running")

        # 注意：实际的TCP服务器启动需要与asyncio.start_server集成
        # 这里只标记状态，实际监听由外部TCP服务器处理
        self.is_running = True
        self.actual_port = self.tcp_config.listen_port

        logger.info(
            f"TCP适配器 '{self.tcp_config.name}' 启动，"
            f"监听 {self.tcp_config.listen_address}:{self.actual_port}"
        )

    async def stop(self):
        """停止TCP适配器"""
        if not self.is_running:
            return

        # 清理所有连接
        self.connections.clear()
        self._stats["active_connections"] = 0

        self.is_running = False
        self.actual_port = 0

        logger.info(f"TCP适配器 '{self.tcp_config.name}' 已停止")

    async def restart(self):
        """重启TCP适配器"""
        await self.stop()
        await self.start()

    async def add_connection(self, connection_id: str, client_address: str, client_port: int):
        """
        添加TCP连接

        Args:
            connection_id: 连接ID（通常是UUID）
            client_address: 客户端地址
            client_port: 客户端端口

        Raises:
            RuntimeError: 如果达到最大连接数
        """
        if len(self.connections) >= self.tcp_config.max_connections:
            raise RuntimeError(
                f"Maximum connections reached ({self.tcp_config.max_connections})"
            )

        self.connections[connection_id] = {
            "client_address": client_address,
            "client_port": client_port,
            "connected_at": datetime.now().isoformat()
        }

        self._stats["active_connections"] = len(self.connections)
        self._stats["total_connections"] += 1

        logger.info(
            f"TCP连接已建立: {connection_id} from {client_address}:{client_port} "
            f"(当前连接数: {len(self.connections)})"
        )

    async def remove_connection(self, connection_id: str):
        """
        移除TCP连接

        Args:
            connection_id: 连接ID
        """
        if connection_id in self.connections:
            conn_info = self.connections[connection_id]
            del self.connections[connection_id]
            self._stats["active_connections"] = len(self.connections)

            logger.info(
                f"TCP连接已断开: {connection_id} from {conn_info['client_address']}:{conn_info['client_port']} "
                f"(当前连接数: {len(self.connections)})"
            )

    async def receive_data(
        self,
        connection_id: str,
        data: bytes,
        client_address: str,
        client_port: int
    ):
        """
        接收TCP数据

        Args:
            connection_id: 连接ID
            data: 数据内容（字节流）
            client_address: 客户端地址
            client_port: 客户端端口
        """
        try:
            # 更新统计
            self._stats["messages_received"] += 1
            self._stats["bytes_received"] += len(data)

            # 构建消息数据
            message_data = {
                "message_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_protocol": ProtocolType.TCP,
                "data_source_id": self.tcp_config.data_source_id,
                "connection_id": connection_id,
                "client_address": client_address,
                "client_port": client_port,
                "raw_data": data,
                "data_size": len(data),
                "adapter_name": self.tcp_config.name
            }

            # 如果配置了帧格式且需要自动解析
            if self.tcp_config.auto_parse and self.frame_parser:
                try:
                    parsed_data = self.frame_parser.parse(data)
                    message_data["parsed_data"] = parsed_data

                    # 发布到解析成功主题
                    self.eventbus.publish(
                        topic=TopicCategory.DATA_PARSED,
                        data=message_data,
                        source="tcp_adapter"
                    )

                    logger.info(f"TCP数据解析成功: {parsed_data}")
                except Exception as parse_error:
                    # 解析失败，记录错误但仍发布原始数据
                    message_data["parse_error"] = str(parse_error)
                    logger.warning(f"TCP数据解析失败: {parse_error}")
                    self._stats["errors"] += 1

            # 发布到EventBus
            self.eventbus.publish(
                topic=TopicCategory.TCP_RECEIVED,
                data=message_data,
                source="tcp_adapter"
            )

            logger.info(
                f"TCP接收数据: {len(data)} bytes from {client_address}:{client_port}"
            )

        except Exception as e:
            logger.error(f"处理TCP数据时出错: {e}", exc_info=True)
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
            "name": self.tcp_config.name,
            "is_running": self.is_running,
            "listen_address": self.tcp_config.listen_address,
            "listen_port": self.tcp_config.listen_port,
            "actual_port": self.actual_port,
            "buffer_size": self.tcp_config.buffer_size,
            "max_connections": self.tcp_config.max_connections,
            "active_connections": len(self.connections),
            "auto_parse": self.tcp_config.auto_parse,
            "has_frame_parser": self.frame_parser is not None,
            **self._stats  # 包含基类统计信息
        }
