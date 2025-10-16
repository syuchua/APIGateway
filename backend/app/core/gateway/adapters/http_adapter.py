"""
HTTP协议适配器实现
接收HTTP请求数据并发布到EventBus
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.frame_schema import FrameSchemaResponse
from app.core.gateway.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class HTTPAdapterConfig(BaseModel):
    """HTTP适配器配置模型"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, description="适配器名称")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    endpoint: str = Field(..., min_length=1, description="HTTP端点路径，如/api/data")
    method: str = Field(default="POST", description="HTTP方法")
    frame_schema_id: Optional[UUID] = Field(None, description="帧格式ID")
    auto_parse: bool = Field(default=False, description="是否自动解析数据帧")
    is_active: bool = Field(default=True, description="是否激活")


class HTTPAdapter(BaseAdapter):
    """
    HTTP协议适配器

    功能：
    - 接收HTTP请求数据
    - 解析数据帧（可选）
    - 发布到EventBus
    - 支持高并发处理
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化HTTP适配器

        Args:
            config: 适配器配置字典（兼容HTTPAdapterConfig）
            eventbus: EventBus实例
            frame_schema: 帧格式定义（可选）
        """
        # 调用父类初始化
        super().__init__(config, eventbus, frame_schema)

        # 如果config是字典，转换为HTTPAdapterConfig
        if isinstance(config, dict):
            self.http_config = HTTPAdapterConfig(**config)
        elif isinstance(config, HTTPAdapterConfig):
            self.http_config = config
        else:
            raise TypeError("config must be dict or HTTPAdapterConfig")

        # HTTP特定属性
        self.frame_parser = None

        # HTTP适配器特定统计（扩展基类统计）
        self._stats["messages_processed"] = 0

        # 如果提供了帧格式定义，创建解析器
        if frame_schema:
            from app.core.gateway.frame.parser import FrameParser
            self.frame_parser = FrameParser(frame_schema)

    async def start(self):
        """启动HTTP适配器"""
        if self.is_running:
            raise RuntimeError(f"HTTP适配器 '{self.http_config.name}' already running")

        self.is_running = True

        logger.info(
            f"HTTP适配器 '{self.http_config.name}' 启动，"
            f"端点: {self.http_config.endpoint}, 方法: {self.http_config.method}"
        )

    async def stop(self):
        """停止HTTP适配器"""
        if not self.is_running:
            return

        self.is_running = False

        logger.info(f"HTTP适配器 '{self.http_config.name}' 已停止")

    async def restart(self):
        """重启HTTP适配器"""
        await self.stop()
        await self.start()

    async def receive_data(
        self,
        data: Any,
        source_address: str,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        接收HTTP请求数据

        Args:
            data: 请求数据（可以是dict、bytes等）
            source_address: 来源IP地址
            headers: HTTP请求头
        """
        try:
            # 更新统计
            self._stats["messages_received"] += 1

            # 构建消息数据
            message_data = {
                "message_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_protocol": ProtocolType.HTTP,
                "data_source_id": self.http_config.data_source_id,
                "source_address": source_address,
                "raw_data": data,
                "adapter_name": self.http_config.name,
                "method": self.http_config.method,
                "endpoint": self.http_config.endpoint
            }

            if headers:
                message_data["headers"] = headers

            # 如果配置了帧格式且需要自动解析，且数据是bytes
            if self.http_config.auto_parse and self.frame_parser and isinstance(data, bytes):
                try:
                    parsed_data = self.frame_parser.parse(data)
                    message_data["parsed_data"] = parsed_data

                    # 发布到解析成功主题
                    self.eventbus.publish(
                        topic=TopicCategory.DATA_PARSED,
                        data=message_data,
                        source="http_adapter"
                    )

                    logger.info(f"HTTP数据解析成功: {parsed_data}")
                except Exception as parse_error:
                    # 解析失败，记录错误但仍发布原始数据
                    message_data["parse_error"] = str(parse_error)
                    logger.warning(f"HTTP数据解析失败: {parse_error}")
                    self._stats["errors"] += 1

            # 发布到EventBus
            self.eventbus.publish(
                topic=TopicCategory.HTTP_RECEIVED,
                data=message_data,
                source="http_adapter"
            )

            self._stats["messages_processed"] += 1

            logger.info(
                f"HTTP接收数据: endpoint={self.http_config.endpoint}, "
                f"from {source_address}"
            )

        except Exception as e:
            logger.error(f"处理HTTP数据时出错: {e}", exc_info=True)
            self._stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "name": self.http_config.name,
            "is_running": self.is_running,
            "endpoint": self.http_config.endpoint,
            "method": self.http_config.method,
            "auto_parse": self.http_config.auto_parse,
            "has_frame_parser": self.frame_parser is not None,
            **self._stats  # 包含父类统计信息
        }

    def get_endpoint_path(self) -> str:
        """获取HTTP端点路径"""
        return self.http_config.endpoint
