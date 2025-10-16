"""
网关管理器 - 统一管理所有网关组件
"""
import logging
import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from app.core.eventbus import SimpleEventBus, get_eventbus
from app.core.gateway.adapters.udp_adapter import UDPAdapter, UDPAdapterConfig
from app.core.gateway.adapters.factory import AdapterFactory
from app.core.gateway.pipeline.data_pipeline import DataPipeline
from app.schemas.frame_schema import FrameSchemaResponse
from app.schemas.routing_rule import RoutingRuleResponse
from app.schemas.target_system import TargetSystemResponse
from app.schemas.common import ProtocolType

logger = logging.getLogger(__name__)


class GatewayManager:
    """
    网关管理器

    功能：
    - 统一管理所有网关组件
    - 协调协议适配器、数据处理管道
    - 提供统一的启动、停止接口
    """

    def __init__(self, eventbus: Optional[SimpleEventBus] = None):
        """
        初始化网关管理器

        Args:
            eventbus: EventBus实例，如果不提供则使用全局实例
        """
        self.eventbus = eventbus or get_eventbus()
        self.is_running = False

        # 核心组件
        self.data_pipeline = DataPipeline(self.eventbus)

        # 协议适配器字典
        self.adapters: Dict[str, UDPAdapter] = {}

        logger.info("网关管理器已初始化")

    async def start(self):
        """启动网关"""
        if self.is_running:
            logger.warning("网关已经在运行中")
            return

        try:
            # 启动数据处理管道
            await self.data_pipeline.start()
            logger.info("数据处理管道已启动")

            # 启动所有适配器
            for adapter_id, adapter in self.adapters.items():
                await adapter.start()
                logger.info(f"适配器 {adapter_id} 已启动")

            self.is_running = True
            logger.info("网关启动成功")

        except Exception as e:
            logger.error(f"网关启动失败: {e}", exc_info=True)
            raise

    async def stop(self):
        """停止网关"""
        if not self.is_running:
            return

        try:
            # 停止所有适配器
            for adapter_id, adapter in list(self.adapters.items()):
                await adapter.stop()
                logger.info(f"适配器 {adapter_id} 已停止")

            # 停止数据处理管道
            await self.data_pipeline.stop()
            logger.info("数据处理管道已停止")

            self.is_running = False
            logger.info("网关已停止")

        except Exception as e:
            logger.error(f"网关停止失败: {e}", exc_info=True)
            raise

    # ==================== 适配器管理 ====================

    async def add_udp_adapter(
        self,
        adapter_id: str,
        config: UDPAdapterConfig,
        frame_schema: Optional[FrameSchemaResponse] = None
    ) -> UDPAdapter:
        """
        添加UDP适配器

        Args:
            adapter_id: 适配器ID
            config: 适配器配置
            frame_schema: 帧格式定义（可选）

        Returns:
            UDPAdapter实例
        """
        if adapter_id in self.adapters:
            raise ValueError(f"适配器 {adapter_id} 已存在")

        adapter = UDPAdapter(config, self.eventbus, frame_schema)
        self.adapters[adapter_id] = adapter

        # 如果网关已运行，立即启动适配器
        if self.is_running:
            await adapter.start()

        logger.info(f"添加UDP适配器: {adapter_id}")
        return adapter

    async def add_adapter(
        self,
        adapter_id: str,
        protocol: ProtocolType,
        config: Dict,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        通用适配器添加方法（使用工厂模式）

        Args:
            adapter_id: 适配器ID
            protocol: 协议类型
            config: 适配器配置字典
            frame_schema: 帧格式定义（可选）

        Returns:
            适配器实例

        Raises:
            ValueError: 如果适配器ID已存在或协议不支持
        """
        if adapter_id in self.adapters:
            raise ValueError(f"适配器 {adapter_id} 已存在")

        # 使用工厂创建适配器
        adapter = AdapterFactory.create(
            protocol=protocol,
            config=config,
            eventbus=self.eventbus,
            frame_schema=frame_schema
        )

        self.adapters[adapter_id] = adapter

        # 如果网关已运行，立即启动适配器
        if self.is_running:
            await adapter.start()

        logger.info(f"添加{protocol.value}适配器: {adapter_id}")
        return adapter

    async def remove_adapter(self, adapter_id: str):
        """
        移除适配器

        Args:
            adapter_id: 适配器ID
        """
        if adapter_id not in self.adapters:
            logger.warning(f"适配器 {adapter_id} 不存在")
            return

        adapter = self.adapters[adapter_id]
        await adapter.stop()
        del self.adapters[adapter_id]

        logger.info(f"移除适配器: {adapter_id}")

    # ==================== 配置管理 ====================

    async def register_frame_schema(self, schema: FrameSchemaResponse):
        """注册帧格式定义"""
        await self.data_pipeline.register_frame_schema(schema)
        logger.info(f"注册帧格式: {schema.name} ({schema.id})")

    async def register_routing_rule(self, rule: RoutingRuleResponse):
        """注册路由规则"""
        await self.data_pipeline.register_routing_rule(rule)
        logger.info(f"注册路由规则: {rule.name} ({rule.id})")

    async def register_target_system(self, target_system: TargetSystemResponse):
        """注册目标系统"""
        await self.data_pipeline.register_target_system(target_system)
        logger.info(f"注册目标系统: {target_system.name} ({target_system.id})")

    async def unregister_frame_schema(self, schema_id: UUID):
        """注销帧格式定义"""
        await self.data_pipeline.unregister_frame_schema(schema_id)
        logger.info(f"注销帧格式: {schema_id}")

    async def unregister_routing_rule(self, rule_id: UUID):
        """注销路由规则"""
        await self.data_pipeline.unregister_routing_rule(rule_id)
        logger.info(f"注销路由规则: {rule_id}")

    async def reload_routing_rule(self, rule: RoutingRuleResponse):
        """重新加载路由规则（先注销再注册最新配置）"""
        try:
            await self.data_pipeline.unregister_routing_rule(rule.id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"注销路由规则 {rule.id} 时出现问题: {exc}")

        await self.data_pipeline.register_routing_rule(rule)
        logger.info(f"重新加载路由规则: {rule.name} ({rule.id})")

    async def unregister_target_system(self, target_id: UUID):
        """注销目标系统"""
        await self.data_pipeline.unregister_target_system(target_id)
        logger.info(f"注销目标系统: {target_id}")

    # ==================== 状态查询 ====================

    def get_status(self) -> Dict:
        """获取网关状态"""
        return {
            "is_running": self.is_running,
            "adapters": {
                adapter_id: adapter.get_stats()
                for adapter_id, adapter in self.adapters.items()
            },
            "pipeline": self.data_pipeline.get_stats()
        }

    def get_adapter_stats(self, adapter_id: str) -> Optional[Dict]:
        """获取适配器统计信息"""
        adapter = self.adapters.get(adapter_id)
        if adapter:
            return adapter.get_stats()
        return None


# 全局网关管理器实例
_gateway_manager: Optional[GatewayManager] = None


def get_gateway_manager() -> GatewayManager:
    """获取全局网关管理器实例（单例）"""
    global _gateway_manager
    if _gateway_manager is None:
        _gateway_manager = GatewayManager()
    return _gateway_manager
