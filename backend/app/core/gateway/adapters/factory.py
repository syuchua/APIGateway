"""
协议适配器工厂
使用工厂模式创建和管理协议适配器
"""
import logging
from typing import Dict, Type, List, Optional

from app.schemas.common import ProtocolType
from app.core.eventbus import SimpleEventBus
from app.core.gateway.adapters.base import BaseAdapter
from app.schemas.frame_schema import FrameSchemaResponse

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    协议适配器工厂

    职责：
    - 注册适配器类型
    - 根据协议类型创建适配器实例
    - 管理支持的协议列表

    使用示例：
        # 注册适配器
        AdapterFactory.register(ProtocolType.UDP, UDPAdapter)

        # 创建实例
        adapter = AdapterFactory.create(
            protocol=ProtocolType.UDP,
            config=config_dict,
            eventbus=eventbus
        )
    """

    # 注册表：协议类型 -> 适配器类
    _adapters: Dict[ProtocolType, Type[BaseAdapter]] = {}

    @classmethod
    def register(cls, protocol: ProtocolType, adapter_class: Type[BaseAdapter]):
        """
        注册适配器类型

        Args:
            protocol: 协议类型
            adapter_class: 适配器类（必须继承BaseAdapter）

        Raises:
            TypeError: 如果adapter_class不是BaseAdapter的子类
        """
        if not issubclass(adapter_class, BaseAdapter):
            raise TypeError(
                f"{adapter_class.__name__} 必须继承 BaseAdapter"
            )

        cls._adapters[protocol] = adapter_class
        logger.info(f"注册适配器: {protocol.value} -> {adapter_class.__name__}")

    @classmethod
    def unregister(cls, protocol: ProtocolType):
        """
        注销适配器类型

        Args:
            protocol: 协议类型
        """
        if protocol in cls._adapters:
            del cls._adapters[protocol]
            logger.info(f"注销适配器: {protocol.value}")

    @classmethod
    def create(
        cls,
        protocol: ProtocolType,
        config: Dict,
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ) -> BaseAdapter:
        """
        创建适配器实例

        Args:
            protocol: 协议类型
            config: 适配器配置字典
            eventbus: EventBus实例
            frame_schema: 帧格式定义（可选）

        Returns:
            适配器实例

        Raises:
            ValueError: 如果协议类型不支持
        """
        adapter_class = cls._adapters.get(protocol)

        if not adapter_class:
            supported = ", ".join([p.value for p in cls.get_supported_protocols()])
            raise ValueError(
                f"不支持的协议类型: {protocol.value}。"
                f"支持的协议: {supported}"
            )

        logger.info(f"创建适配器: {protocol.value} ({adapter_class.__name__})")

        return adapter_class(
            config=config,
            eventbus=eventbus,
            frame_schema=frame_schema
        )

    @classmethod
    def get_supported_protocols(cls) -> List[ProtocolType]:
        """
        获取支持的协议列表

        Returns:
            支持的协议类型列表
        """
        return list(cls._adapters.keys())

    @classmethod
    def is_supported(cls, protocol: ProtocolType) -> bool:
        """
        检查协议是否支持

        Args:
            protocol: 协议类型

        Returns:
            如果支持返回True
        """
        return protocol in cls._adapters

    @classmethod
    def get_adapter_class(cls, protocol: ProtocolType) -> Optional[Type[BaseAdapter]]:
        """
        获取协议对应的适配器类

        Args:
            protocol: 协议类型

        Returns:
            适配器类，如果不存在返回None
        """
        return cls._adapters.get(protocol)
