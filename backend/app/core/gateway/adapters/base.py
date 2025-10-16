"""
协议适配器基类
定义所有协议适配器的统一接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.eventbus import SimpleEventBus
from app.schemas.frame_schema import FrameSchemaResponse


class BaseAdapter(ABC):
    """
    协议适配器抽象基类

    所有协议适配器必须继承此类并实现抽象方法

    职责：
    - 接收特定协议的数据
    - 转换为统一格式
    - 发布到EventBus
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化适配器

        Args:
            config: 适配器配置字典
            eventbus: EventBus实例
            frame_schema: 帧格式定义（可选）
        """
        self.config = config
        self.eventbus = eventbus
        self.frame_schema = frame_schema
        self.is_running = False

        # 统计信息
        self._stats = {
            "messages_received": 0,
            "messages_published": 0,
            "errors": 0,
            "bytes_received": 0
        }

    @abstractmethod
    async def start(self):
        """
        启动适配器

        Raises:
            RuntimeError: 如果启动失败
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        停止适配器

        应该优雅地关闭连接，释放资源
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取适配器统计信息

        Returns:
            包含统计数据的字典
        """
        pass

    def _increment_stats(self, key: str, value: int = 1):
        """
        增加统计计数

        Args:
            key: 统计项名称
            value: 增加的值
        """
        if key in self._stats:
            self._stats[key] += value

    def _publish_to_eventbus(
        self,
        raw_data: bytes,
        source_info: Dict[str, Any]
    ):
        """
        发布消息到EventBus（通用方法）

        Args:
            raw_data: 原始数据
            source_info: 来源信息（protocol, source_id, source_address等）
        """
        from app.core.eventbus.topics import TopicCategory
        from datetime import datetime
        from uuid import uuid4

        # 构建统一消息格式
        message = {
            "message_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "raw_data": raw_data,
            **source_info
        }

        # 发布到EventBus
        self.eventbus.publish(
            topic=TopicCategory.DATA_RECEIVED,
            data=message,
            source=f"{self.config.get('name', 'adapter')}"
        )

        self._increment_stats("messages_published")
