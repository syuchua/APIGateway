"""
转发器工厂
使用工厂模式创建和管理转发器
"""
import logging
from typing import Dict, Type, List, Optional

from app.schemas.common import ProtocolType
from app.core.gateway.forwarder.base import BaseForwarder

logger = logging.getLogger(__name__)


class ForwarderFactory:
    """
    转发器工厂

    职责：
    - 注册转发器类型
    - 根据协议类型创建转发器实例
    - 管理支持的协议列表

    使用示例：
        # 注册转发器
        ForwarderFactory.register(ProtocolType.HTTP, HTTPForwarder)

        # 创建实例
        forwarder = ForwarderFactory.create(
            protocol=ProtocolType.HTTP,
            config=config_dict
        )
    """

    # 注册表：协议类型 -> 转发器类
    _forwarders: Dict[ProtocolType, Type[BaseForwarder]] = {}

    @classmethod
    def register(cls, protocol: ProtocolType, forwarder_class: Type[BaseForwarder]):
        """
        注册转发器类型

        Args:
            protocol: 协议类型
            forwarder_class: 转发器类（必须继承BaseForwarder）

        Raises:
            TypeError: 如果forwarder_class不是BaseForwarder的子类
        """
        if not issubclass(forwarder_class, BaseForwarder):
            raise TypeError(
                f"{forwarder_class.__name__} 必须继承 BaseForwarder"
            )

        cls._forwarders[protocol] = forwarder_class
        logger.info(f"注册转发器: {protocol.value} -> {forwarder_class.__name__}")

    @classmethod
    def unregister(cls, protocol: ProtocolType):
        """
        注销转发器类型

        Args:
            protocol: 协议类型
        """
        if protocol in cls._forwarders:
            del cls._forwarders[protocol]
            logger.info(f"注销转发器: {protocol.value}")

    @classmethod
    def create(cls, protocol: ProtocolType, config: Dict) -> BaseForwarder:
        """
        创建转发器实例

        Args:
            protocol: 协议类型
            config: 转发器配置字典

        Returns:
            转发器实例

        Raises:
            ValueError: 如果协议类型不支持
        """
        forwarder_class = cls._forwarders.get(protocol)

        if not forwarder_class:
            supported = ", ".join([p.value for p in cls.get_supported_protocols()])
            raise ValueError(
                f"不支持的协议类型: {protocol.value}。"
                f"支持的协议: {supported}"
            )

        logger.info(f"创建转发器: {protocol.value} ({forwarder_class.__name__})")

        return forwarder_class(config=config)

    @classmethod
    def get_supported_protocols(cls) -> List[ProtocolType]:
        """
        获取支持的协议列表

        Returns:
            支持的协议类型列表
        """
        return list(cls._forwarders.keys())

    @classmethod
    def is_supported(cls, protocol: ProtocolType) -> bool:
        """
        检查协议是否支持

        Args:
            protocol: 协议类型

        Returns:
            如果支持返回True
        """
        return protocol in cls._forwarders

    @classmethod
    def get_forwarder_class(cls, protocol: ProtocolType) -> Optional[Type[BaseForwarder]]:
        """
        获取协议对应的转发器类

        Args:
            protocol: 协议类型

        Returns:
            转发器类，如果不存在返回None
        """
        return cls._forwarders.get(protocol)
