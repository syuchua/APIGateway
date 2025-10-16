"""
数据处理管道实现
统一编排数据流：接收 → 解析 → 路由 → 转换 → 转发
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.core.eventbus import SimpleEventBus, TopicCategory, PROTOCOL_TOPICS
from app.schemas.frame_schema import FrameSchemaResponse
from app.schemas.routing_rule import RoutingRuleResponse
from app.schemas.target_system import TargetSystemResponse
from app.schemas.common import ProtocolType
from app.core.gateway.frame.parser import FrameParser
from app.core.gateway.routing.engine import RoutingEngine
from app.core.gateway.forwarder.forwarder_manager import ForwarderManager
from app.services.monitoring_service import get_monitoring_service
from app.services.crypto_service import get_crypto_service, CryptoServiceError

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    数据处理管道

    功能：
    - 统一编排数据流
    - 集成FrameParser、RoutingEngine、ForwarderManager
    - 订阅EventBus主题自动处理数据
    - 提供组件注册和管理接口
    """

    def __init__(self, eventbus: SimpleEventBus):
        """
        初始化数据处理管道

        Args:
            eventbus: EventBus实例
        """
        self.eventbus = eventbus
        self.is_running = False

        # 创建组件字典
        self.frame_parsers: Dict[str, FrameParser] = {}  # schema_id -> parser
        self.routing_engine = RoutingEngine(eventbus)
        self.forwarder_manager = ForwarderManager(eventbus)
        self._protocol_subscriptions: List[str] = []
        self.monitoring_service = get_monitoring_service(eventbus)
        self.crypto_service = get_crypto_service()

    async def start(self):
        """启动数据处理管道"""
        if self.is_running:
            logger.warning("数据处理管道已经启动")
            return

        # 启动各个组件的自动处理
        # FrameParser没有自动处理机制，在DATA_RECEIVED事件中手动调用
        self.routing_engine.start_auto_routing()
        self.forwarder_manager.start_auto_forward()

        loop = asyncio.get_running_loop()

        def _handler_factory():
            def handler(payload, topic, source):
                logger.info("[Pipeline] Received event topic=%s source=%s keys=%s", topic, source, list(payload.keys()) if isinstance(payload, dict) else type(payload))
                loop.call_soon_threadsafe(asyncio.create_task, self._process_protocol_message(payload, topic, source))

            return handler

        for topic in PROTOCOL_TOPICS:
            topic_str = topic.value if isinstance(topic, TopicCategory) else str(topic)
            subscription_id = self.eventbus.subscribe(topic_str, _handler_factory())
            self._protocol_subscriptions.append(subscription_id)

        self.is_running = True
        logger.info("数据处理管道已启动")

    async def stop(self):
        """停止数据处理管道"""
        if not self.is_running:
            return

        # 停止自动处理
        self.routing_engine.stop_auto_routing()
        self.forwarder_manager.stop_auto_forward()

        # 关闭资源
        await self.forwarder_manager.close()

        for sub_id in self._protocol_subscriptions:
            self.eventbus.unsubscribe(sub_id)
        self._protocol_subscriptions.clear()

        self.is_running = False
        logger.info("数据处理管道已停止")

    # ==================== 帧格式管理 ====================

    async def register_frame_schema(self, schema: FrameSchemaResponse):
        """
        注册帧格式定义

        Args:
            schema: 帧格式定义
        """
        schema_id = str(schema.id)
        self.frame_parsers[schema_id] = FrameParser(schema)
        logger.info(f"注册帧格式: {schema.name} ({schema.id})")

    async def unregister_frame_schema(self, schema_id: UUID):
        """
        注销帧格式定义

        Args:
            schema_id: 帧格式ID
        """
        schema_id_str = str(schema_id)
        if schema_id_str in self.frame_parsers:
            del self.frame_parsers[schema_id_str]
        logger.info(f"注销帧格式: {schema_id}")

    # ==================== 路由规则管理 ====================

    async def register_routing_rule(self, rule: RoutingRuleResponse):
        """
        注册路由规则

        Args:
            rule: 路由规则
        """
        self.routing_engine.add_rule(rule)
        logger.info(f"注册路由规则: {rule.name} ({rule.id})")

    async def unregister_routing_rule(self, rule_id: UUID):
        """
        注销路由规则

        Args:
            rule_id: 路由规则ID
        """
        self.routing_engine.remove_rule(rule_id)
        logger.info(f"注销路由规则: {rule_id}")

    # ==================== 目标系统管理 ====================

    async def register_target_system(self, target_system: TargetSystemResponse):
        """
        注册目标系统

        Args:
            target_system: 目标系统配置
        """
        await self.forwarder_manager.register_target_system(target_system)
        logger.info(f"注册目标系统: {target_system.name} ({target_system.id})")

    async def unregister_target_system(self, target_id: UUID):
        """
        注销目标系统

        Args:
            target_id: 目标系统ID
        """
        await self.forwarder_manager.unregister_target_system(target_id)
        logger.info(f"注销目标系统: {target_id}")

    # ==================== 统计信息 ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        获取管道统计信息

        Returns:
            统计信息字典
        """
        return {
            "is_running": self.is_running,
            "frame_parsers": len(self.frame_parsers),
            "routing_rules": len(self.routing_engine.rules),
            "target_systems": self.forwarder_manager.get_stats()["total_targets"],
            "active_targets": self.forwarder_manager.get_stats()["active_targets"],
            "routing_stats": self.routing_engine.get_stats(),
            "forwarder_stats": self.forwarder_manager.get_stats()
        }

    # ==================== 手动处理接口 ====================

    async def _process_protocol_message(self, data: Dict[str, Any], topic: str, source: Optional[str]) -> None:
        """处理来自协议层的原始消息并触发路由"""

        if not isinstance(data, dict):
            logger.info("忽略非字典消息: %s", type(data))
            return

        message = dict(data)

        self._decrypt_message_if_needed(message)

        raw = message.get("raw_data")
        if isinstance(raw, (bytes, bytearray)):
            try:
                message["raw_data"] = raw.decode("utf-8")
            except UnicodeDecodeError:
                message["raw_data"] = raw.hex()

        message.setdefault("protocol_topic", topic)
        if "source_protocol" not in message:
            try:
                prefix = topic.split("_")[0]
                message["source_protocol"] = ProtocolType(prefix)
            except Exception:  # pylint: disable=broad-except
                pass
        else:
            proto_value = message["source_protocol"]
            if isinstance(proto_value, str):
                try:
                    message["source_protocol"] = ProtocolType(proto_value.upper())
                except Exception:
                    message["source_protocol"] = proto_value.upper()

        if "parsed_data" not in message:
            raw = message.get("raw_data")
            parsed_value: Any = None
            if isinstance(raw, (bytes, bytearray)):
                try:
                    decoded = raw.decode("utf-8")
                    message.setdefault("raw_text", decoded)
                    try:
                        parsed_value = json.loads(decoded)
                    except json.JSONDecodeError:
                        parsed_value = decoded
                except UnicodeDecodeError:
                    parsed_value = raw.hex()
            elif isinstance(raw, str):
                try:
                    parsed_value = json.loads(raw)
                except json.JSONDecodeError:
                    parsed_value = raw
            elif isinstance(raw, dict):
                parsed_value = raw
            elif raw is not None:
                parsed_value = raw

            if parsed_value is not None:
                message["parsed_data"] = parsed_value

        if message.get("data_source_id") is not None:
            message["data_source_id"] = str(message["data_source_id"])

        if "adapter_name" in message:
            message.setdefault("source_name", message["adapter_name"])

        try:
            logger.info(
                "[Pipeline] Routing message protocol=%s source_id=%s sample=%s",
                message.get("source_protocol"),
                message.get("data_source_id"),
                message.get("parsed_data") or message.get("raw_text") or message.get("raw_data")
            )
            routing_result = self.routing_engine.route_message(message)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("路由协议消息失败: %s", exc, exc_info=True)
        else:
            try:
                await self.monitoring_service.record_routing_decision(routing_result)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("记录监控数据失败: %s", exc, exc_info=True)

    async def process_message(self, raw_data: bytes, frame_schema_id: UUID, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        手动处理单条消息（用于测试或特殊场景）

        Args:
            raw_data: 原始数据
            frame_schema_id: 帧格式ID
            source_info: 来源信息（protocol, source_id等）

        Returns:
            处理结果
        """
        try:
            # 1. 获取parser并解析
            schema_id_str = str(frame_schema_id)
            if schema_id_str not in self.frame_parsers:
                return {
                    "success": False,
                    "stage": "parse",
                    "error": f"Frame schema {schema_id_str} not found"
                }

            parser = self.frame_parsers[schema_id_str]
            parsed_data = parser.parse(raw_data)

            # 2. 构建消息数据
            message_data = {
                **source_info,
                "parsed_data": parsed_data
            }

            # 3. 路由
            self._decrypt_message_if_needed(message_data)
            routing_result = self.routing_engine.route_message(message_data)
            await self.monitoring_service.record_routing_decision(routing_result)

            if not routing_result.get("target_system_ids"):
                return {
                    "success": True,
                    "stage": "route",
                    "message": "No matching routing rules"
                }

            # 4. 转发
            target_ids = [UUID(tid) for tid in routing_result["target_system_ids"]]
            forward_results = await self.forwarder_manager.forward_to_targets(message_data, target_ids)
            await self.monitoring_service.record_forward_results(routing_result, forward_results)

            return {
                "success": True,
                "stage": "complete",
                "routing_result": routing_result,
                "forward_results": forward_results
            }

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _decrypt_message_if_needed(self, message: Dict[str, Any]) -> None:
        """解密包含encrypted_payload的消息"""
        encrypted_payload = message.get("encrypted_payload")
        if not encrypted_payload:
            return

        try:
            decrypted_dict = self.crypto_service.unwrap_payload(encrypted_payload)
        except CryptoServiceError as exc:
            logger.error("解密消息失败: %s", exc)
            message["decryption_error"] = str(exc)
            return

        try:
            raw_text = json.dumps(decrypted_dict, ensure_ascii=False)
            message["raw_text"] = raw_text
            message["raw_data"] = raw_text.encode("utf-8")
        except (TypeError, ValueError):
            # 如果无法转成JSON字符串，则仅保留结构化数据
            message.pop("raw_text", None)
            message.pop("raw_data", None)

        message["parsed_data"] = decrypted_dict
        message["is_encrypted"] = True
        message.pop("encrypted_payload", None)
