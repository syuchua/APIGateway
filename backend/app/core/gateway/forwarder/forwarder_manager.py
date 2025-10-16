"""
转发器管理器实现
管理多个转发器,根据路由结果转发数据到目标系统
"""
import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from uuid import UUID

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.core.gateway.forwarder import ForwarderFactory
from app.schemas.target_system import TargetSystemResponse
from app.schemas.common import ProtocolType
from app.schemas.forwarder import (
    ForwardStatus,
    HTTPForwarderConfig,
    HTTPMethod,
    MQTTForwarderConfig,
    UDPForwarderConfig,
    TCPForwarderConfig,
    WebSocketForwarderConfig,
)

# 避免循环导入
if TYPE_CHECKING:
    from app.core.gateway.pipeline.transformer import DataTransformer, TransformConfig
from app.services.monitoring_service import get_monitoring_service
from app.services.crypto_service import get_crypto_service, CryptoServiceError

logger = logging.getLogger(__name__)


class ForwarderManager:
    """
    转发器管理器

    功能：
    - 管理多个目标系统和对应的转发器
    - 根据路由结果转发数据
    - 支持数据转换
    - 自动订阅ROUTING_DECIDED主题
    """

    def __init__(self, eventbus: SimpleEventBus):
        """
        初始化转发器管理器

        Args:
            eventbus: EventBus实例
        """
        self.eventbus = eventbus
        self.target_systems: Dict[str, TargetSystemResponse] = {}
        self.forwarders: Dict[str, Any] = {}  # target_id -> forwarder
        self.transformers: Dict[str, Any] = {}  # target_id -> DataTransformer
        self.forwarder_errors: Dict[str, str] = {}
        self._auto_forward_active = False
        self.monitoring_service = get_monitoring_service(eventbus)
        self.crypto_service = get_crypto_service()

    async def register_target_system(self, target_system: TargetSystemResponse):
        """
        注册目标系统

        Args:
            target_system: 目标系统配置
        """
        # 延迟导入避免循环依赖
        from app.core.gateway.pipeline.transformer import DataTransformer, TransformConfig

        target_id = str(target_system.id)

        # 保存目标系统
        self.target_systems[target_id] = target_system

        # 创建转发器
        forwarder = await self._create_forwarder(target_system)
        if forwarder:
            self.forwarders[target_id] = forwarder
        else:
            error_message = self.forwarder_errors.get(target_id)
            if error_message:
                logger.warning(
                    "目标系统 %s (%s) 未初始化转发器: %s",
                    target_system.name,
                    target_id,
                    error_message,
                )

        # 创建数据转换器（如果配置了）
        if target_system.transform_config:
            transform_config = TransformConfig(**target_system.transform_config)
            self.transformers[target_id] = DataTransformer(transform_config)

        logger.info(f"注册目标系统: {target_system.name} ({target_id})")

    async def unregister_target_system(self, target_id: UUID):
        """
        注销目标系统

        Args:
            target_id: 目标系统ID
        """
        target_id_str = str(target_id)

        # 关闭转发器
        if target_id_str in self.forwarders:
            forwarder = self.forwarders[target_id_str]
            if hasattr(forwarder, 'close'):
                await forwarder.close()
            del self.forwarders[target_id_str]

        # 删除转换器
        if target_id_str in self.transformers:
            del self.transformers[target_id_str]

        # 删除目标系统
        if target_id_str in self.target_systems:
            del self.target_systems[target_id_str]

        # 清理错误记录
        self.forwarder_errors.pop(target_id_str, None)

        logger.info(f"注销目标系统: {target_id_str}")

    async def forward_to_targets(
        self,
        data: Dict[str, Any],
        target_ids: List[UUID]
    ) -> List[Dict[str, Any]]:
        """
        转发数据到指定的目标系统

        Args:
            data: 要转发的数据
            target_ids: 目标系统ID列表

        Returns:
            转发结果列表
        """
        tasks = []
        results = []

        for target_id in target_ids:
            target_id_str = str(target_id)

            # 检查目标系统是否存在
            if target_id_str not in self.target_systems:
                logger.warning(f"目标系统不存在: {target_id_str}")
                results.append({
                    "target_id": target_id_str,
                    "status": ForwardStatus.FAILED,
                    "error": f"Target system {target_id_str} not found"
                })
                continue

            # 检查转发器是否存在，不存在时尝试重新创建
            if target_id_str not in self.forwarders:
                logger.warning(f"转发器不存在，尝试重新创建: {target_id_str}")
                recreated = await self._create_forwarder(self.target_systems[target_id_str])
                if recreated:
                    self.forwarders[target_id_str] = recreated
                else:
                    results.append({
                        "target_id": target_id_str,
                        "status": ForwardStatus.FAILED,
                        "error": self.forwarder_errors.get(
                            target_id_str,
                            f"Forwarder for {target_id_str} not available"
                        )
                    })
                    continue

            # 创建转发任务
            task = self._forward_to_single_target(target_id_str, data)
            tasks.append(task)

        # 并发执行所有转发任务
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend([r for r in task_results if not isinstance(r, Exception)])

        return results

    async def _forward_to_single_target(
        self,
        target_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        转发到单个目标系统

        Args:
            target_id: 目标系统ID
            data: 要转发的数据

        Returns:
            转发结果
        """
        try:
            # 数据转换（如果配置了）
            transformed_data = data
            if target_id in self.transformers:
                transformed_data = self.transformers[target_id].transform(data)

            payload = dict(transformed_data)
            payload.setdefault("target_id", target_id)

            encryption_cfg = self._get_encryption_config(target_id)
            if encryption_cfg and encryption_cfg.get("enabled"):
                if "encrypted_payload" not in payload:
                    try:
                        payload = self._encrypt_payload(payload, encryption_cfg)
                        payload.setdefault("target_id", target_id)
                    except CryptoServiceError as exc:
                        logger.error("加密数据失败: %s", exc)
                        return {
                            "target_id": target_id,
                            "status": ForwardStatus.FAILED,
                            "error": str(exc)
                        }

            # 转发
            forwarder = self.forwarders[target_id]
            result = await forwarder.forward(payload)

            return {
                "target_id": target_id,
                "status": result.status,
                "status_code": result.status_code,
                "error": result.error,
                "duration": result.duration
            }

        except Exception as e:
            logger.error(f"转发到 {target_id} 失败: {e}", exc_info=True)
            return {
                "target_id": target_id,
                "status": ForwardStatus.FAILED,
                "error": str(e)
            }

    @staticmethod
    def _coerce_dict(value: Any) -> Dict[str, Any]:
        """将对象转换为字典"""
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return {}

    def _get_encryption_config(self, target_id: str) -> Optional[Dict[str, Any]]:
        target = self.target_systems.get(target_id)
        if target is None:
            return None

        cfg = self._coerce_dict(getattr(target, "forwarder_config", {}))
        encryption_cfg = cfg.get("encryption") or cfg.get("encryption_config")
        if not encryption_cfg:
            return None
        if isinstance(encryption_cfg, bool):
            return {"enabled": bool(encryption_cfg)}
        return self._coerce_dict(encryption_cfg)

    def _encrypt_payload(self, payload: Dict[str, Any], encryption_cfg: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = self._sanitize_payload(payload)
        serialized = json.dumps(sanitized, ensure_ascii=False).encode("utf-8")
        encrypted = self.crypto_service.encrypt_message(serialized)
        envelope = {
            "encrypted_payload": encrypted,
            "encryption": {
                "algorithm": encrypted.get("algorithm", "AES-256-GCM"),
                "version": encryption_cfg.get("version", "v1"),
            },
        }

        metadata = self._coerce_dict(encryption_cfg.get("metadata"))
        if metadata:
            envelope["encryption"].update(metadata)

        return envelope

    def _sanitize_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {k: self._sanitize_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload]
        if isinstance(payload, tuple):
            return [self._sanitize_payload(item) for item in payload]
        if isinstance(payload, (bytes, bytearray)):
            if not payload:
                return ""
            return base64.b64encode(bytes(payload)).decode("ascii")
        if isinstance(payload, datetime):
            return payload.isoformat()
        return payload

    @staticmethod
    def _normalize_path(path: Optional[str]) -> str:
        """确保URL路径以/开头"""
        if not path:
            return "/"
        return path if path.startswith("/") else f"/{path.lstrip('/')}"

    @staticmethod
    def _coerce_protocol(protocol: Any) -> ProtocolType:
        """确保协议类型为ProtocolType枚举"""
        if isinstance(protocol, ProtocolType):
            return protocol
        if isinstance(protocol, str):
            return ProtocolType(protocol.upper())
        raise ValueError(f"无法识别的协议类型: {protocol}")

    @staticmethod
    def _prepare_auth(headers: Dict[str, str], auth_cfg: Dict[str, Any], *, include_basic_header: bool = False):
        """根据认证配置补充头信息，并返回用户名/密码"""
        username = None
        password = None

        if not auth_cfg:
            return headers, username, password

        auth_type = str(auth_cfg.get("auth_type", "none")).lower()

        if auth_type == "basic":
            username = auth_cfg.get("username")
            password = auth_cfg.get("password")
            if include_basic_header and username is not None and password is not None:
                token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
                headers.setdefault("Authorization", f"Basic {token}")
        elif auth_type == "bearer":
            token = auth_cfg.get("token")
            if token:
                headers.setdefault("Authorization", f"Bearer {token}")
        elif auth_type == "api_key":
            api_key = auth_cfg.get("api_key")
            header_name = auth_cfg.get("api_key_header") or "X-API-Key"
            if api_key:
                headers.setdefault(header_name, str(api_key))
        elif auth_type == "custom":
            custom_headers = auth_cfg.get("custom_headers") or {}
            for key, value in custom_headers.items():
                headers.setdefault(str(key), str(value))

        return headers, username, password

    async def _create_forwarder(self, target_system: TargetSystemResponse):
        """
        根据目标系统创建对应的转发器

        Args:
            target_system: 目标系统配置

        Returns:
            转发器实例
        """
        target_id = str(target_system.id)
        forwarder_cfg = self._coerce_dict(getattr(target_system, "forwarder_config", None))
        auth_cfg = self._coerce_dict(getattr(target_system, "auth_config", None))
        if not auth_cfg and forwarder_cfg.get("auth_config"):
            auth_cfg = self._coerce_dict(forwarder_cfg.get("auth_config"))

        try:
            protocol = self._coerce_protocol(target_system.protocol_type)

            builders = {
                ProtocolType.HTTP: self._build_http_forwarder_config,
                ProtocolType.MQTT: self._build_mqtt_forwarder_config,
                ProtocolType.UDP: self._build_udp_forwarder_config,
                ProtocolType.TCP: self._build_tcp_forwarder_config,
                ProtocolType.WEBSOCKET: self._build_websocket_forwarder_config,
            }

            builder = builders.get(protocol)
            if not builder:
                message = f"暂不支持的目标系统协议: {protocol.value}"
                self.forwarder_errors[target_id] = message
                logger.warning(message)
                return None

            if not ForwarderFactory.is_supported(protocol):
                message = f"协议 {protocol.value} 的转发器尚未注册，无法创建"
                self.forwarder_errors[target_id] = message
                logger.warning(message)
                return None

            config = builder(target_system, forwarder_cfg, auth_cfg)
            forwarder = ForwarderFactory.create(protocol, config)
            self.forwarder_errors.pop(target_id, None)
            return forwarder

        except Exception as e:
            error_message = str(e)
            self.forwarder_errors[target_id] = error_message
            logger.error(f"创建转发器失败: {error_message}", exc_info=True)
            return None

    def _build_http_forwarder_config(
        self,
        target_system: TargetSystemResponse,
        forwarder_cfg: Dict[str, Any],
        auth_cfg: Dict[str, Any],
    ) -> HTTPForwarderConfig:
        host = target_system.target_address or forwarder_cfg.get("target_address")
        port = forwarder_cfg.get("target_port", target_system.target_port)
        if not host or not port:
            raise ValueError("HTTP 目标系统缺少目标地址或端口")
        port = int(port)

        use_ssl = bool(forwarder_cfg.get("use_ssl", forwarder_cfg.get("ssl", False)))
        scheme = "https" if use_ssl else "http"
        path = self._normalize_path(forwarder_cfg.get("endpoint_path") or target_system.endpoint_path)
        url = f"{scheme}://{host}:{port}{path}"

        method_value = str(forwarder_cfg.get("method", "POST")).upper()
        try:
            method = HTTPMethod(method_value)
        except ValueError:
            method = HTTPMethod.POST

        headers = {str(k): str(v) for k, v in (forwarder_cfg.get("headers") or {}).items()}
        headers, username, password = self._prepare_auth(headers, auth_cfg)
        if username is None:
            username = forwarder_cfg.get("username")
        if password is None:
            password = forwarder_cfg.get("password")

        timeout = int(forwarder_cfg.get("timeout", target_system.timeout or 30))
        retry_times = int(forwarder_cfg.get("retry_count", target_system.retry_count or 3))
        retry_delay = float(forwarder_cfg.get("retry_delay", 1.0))

        verify_ssl = forwarder_cfg.get("verify_ssl")
        if verify_ssl is None:
            verify_ssl = use_ssl
        else:
            verify_ssl = bool(verify_ssl)

        return HTTPForwarderConfig(
            url=url,
            method=method,
            headers=headers,
            timeout=timeout,
            retry_times=retry_times,
            retry_delay=retry_delay,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

    def _build_mqtt_forwarder_config(
        self,
        target_system: TargetSystemResponse,
        forwarder_cfg: Dict[str, Any],
        auth_cfg: Dict[str, Any],
    ) -> MQTTForwarderConfig:
        host = forwarder_cfg.get("broker_host") or target_system.target_address
        port = forwarder_cfg.get("broker_port") or forwarder_cfg.get("target_port") or target_system.target_port or 1883
        if not host or not port:
            raise ValueError("MQTT 目标系统缺少 broker 主机或端口")

        topic = forwarder_cfg.get("topic") or forwarder_cfg.get("topics")
        if isinstance(topic, list):
            topic = topic[0] if topic else None
        if topic is None:
            topic = f"gateway/{target_system.id}"

        username = auth_cfg.get("username") or forwarder_cfg.get("username")
        password = auth_cfg.get("password") or forwarder_cfg.get("password")

        return MQTTForwarderConfig(
            host=str(host),
            port=int(port),
            username=username,
            password=password,
            topic=str(topic),
            qos=int(forwarder_cfg.get("qos", 1)),
            retain=bool(forwarder_cfg.get("retain", False)),
            client_id=forwarder_cfg.get("client_id"),
            keepalive=int(forwarder_cfg.get("keepalive", forwarder_cfg.get("keep_alive", 60))),
            timeout=int(forwarder_cfg.get("timeout", target_system.timeout if hasattr(target_system, "timeout") else 10)),
            retry_times=int(forwarder_cfg.get("retry_count", target_system.retry_count if hasattr(target_system, "retry_count") else 3)),
            retry_delay=float(forwarder_cfg.get("retry_delay", 1.0)),
            tls_enabled=bool(forwarder_cfg.get("tls_enabled", False)),
            ca_cert=forwarder_cfg.get("ca_cert"),
            cert_file=forwarder_cfg.get("cert_file"),
            key_file=forwarder_cfg.get("key_file"),
        )

    def _build_udp_forwarder_config(
        self,
        target_system: TargetSystemResponse,
        forwarder_cfg: Dict[str, Any],
        _: Dict[str, Any],
    ) -> UDPForwarderConfig:
        host = forwarder_cfg.get("target_address") or target_system.target_address
        port = forwarder_cfg.get("target_port") or target_system.target_port
        if not host or not port:
            raise ValueError("UDP 目标系统缺少目标地址或端口")

        return UDPForwarderConfig(
            host=str(host),
            port=int(port),
            timeout=int(forwarder_cfg.get("timeout", 5)),
            retry_times=int(forwarder_cfg.get("retry_count", 1)),
            retry_delay=float(forwarder_cfg.get("retry_delay", 0.1)),
            buffer_size=int(forwarder_cfg.get("buffer_size", 8192)),
            encoding=str(forwarder_cfg.get("encoding", "utf-8")),
        )

    def _build_tcp_forwarder_config(
        self,
        target_system: TargetSystemResponse,
        forwarder_cfg: Dict[str, Any],
        auth_cfg: Dict[str, Any],  # noqa: ARG002 - 预留将来扩展
    ) -> TCPForwarderConfig:
        host = forwarder_cfg.get("target_address") or target_system.target_address
        port = forwarder_cfg.get("target_port") or target_system.target_port
        if not host or not port:
            raise ValueError("TCP 目标系统缺少目标地址或端口")

        return TCPForwarderConfig(
            host=str(host),
            port=int(port),
            timeout=int(forwarder_cfg.get("timeout", target_system.timeout if hasattr(target_system, "timeout") else 30)),
            retry_times=int(forwarder_cfg.get("retry_count", target_system.retry_count if hasattr(target_system, "retry_count") else 3)),
            retry_delay=float(forwarder_cfg.get("retry_delay", 1.0)),
            buffer_size=int(forwarder_cfg.get("buffer_size", 8192)),
            encoding=str(forwarder_cfg.get("encoding", "utf-8")),
            keep_alive=bool(forwarder_cfg.get("keep_alive", True)),
            newline=str(forwarder_cfg.get("newline", "\n")),
        )

    def _build_websocket_forwarder_config(
        self,
        target_system: TargetSystemResponse,
        forwarder_cfg: Dict[str, Any],
        auth_cfg: Dict[str, Any],
    ) -> WebSocketForwarderConfig:
        host = forwarder_cfg.get("target_address") or target_system.target_address
        port = forwarder_cfg.get("target_port") or target_system.target_port
        if not host or not port:
            raise ValueError("WebSocket 目标系统缺少目标地址或端口")
        port = int(port)

        use_ssl = bool(forwarder_cfg.get("use_ssl", forwarder_cfg.get("ssl", False)))
        scheme = "wss" if use_ssl else "ws"
        path = self._normalize_path(forwarder_cfg.get("endpoint_path") or target_system.endpoint_path)
        url = f"{scheme}://{host}:{port}{path}"

        headers = {str(k): str(v) for k, v in (forwarder_cfg.get("headers") or {}).items()}
        headers, _, _ = self._prepare_auth(headers, auth_cfg, include_basic_header=True)

        return WebSocketForwarderConfig(
            url=url,
            headers=headers,
            timeout=int(forwarder_cfg.get("timeout", target_system.timeout if hasattr(target_system, "timeout") else 30)),
            retry_times=int(forwarder_cfg.get("retry_count", target_system.retry_count if hasattr(target_system, "retry_count") else 3)),
            retry_delay=float(forwarder_cfg.get("retry_delay", 1.0)),
            ping_interval=int(forwarder_cfg.get("ping_interval", 30)),
            ping_timeout=int(forwarder_cfg.get("ping_timeout", 10)),
            close_timeout=int(forwarder_cfg.get("close_timeout", 10)),
        )

    def start_auto_forward(self):
        """启动自动转发（订阅ROUTING_DECIDED主题）"""
        if self._auto_forward_active:
            logger.warning("自动转发已经启动")
            return

        def on_routing_decided(data, topic, source):
            """处理路由决策结果"""
            try:
                # 提取目标系统ID列表
                target_ids_str = data.get("target_system_ids", [])
                if not target_ids_str:
                    logger.info("没有目标系统，跳过转发")
                    return

                # 转换为UUID
                from uuid import UUID
                target_ids = [UUID(tid) for tid in target_ids_str]

                # 创建异步任务转发
                async def forward_task():
                    results = await self.forward_to_targets(data, target_ids)

                    # 发布转发结果
                    self.eventbus.publish(
                        topic=TopicCategory.DATA_FORWARDED,
                        data={
                            **data,
                            "forward_results": results
                        },
                        source="forwarder_manager"
                    )
                    try:
                        await self.monitoring_service.record_forward_results(data, results)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.warning("记录转发监控数据失败: %s", exc, exc_info=True)

                # 在事件循环中执行
                asyncio.create_task(forward_task())

            except Exception as e:
                logger.error(f"处理路由决策失败: {e}", exc_info=True)

        self.eventbus.subscribe(TopicCategory.ROUTING_DECIDED, on_routing_decided)
        self._auto_forward_active = True
        logger.info("自动转发已启动")

    def stop_auto_forward(self):
        """停止自动转发"""
        self._auto_forward_active = False
        logger.info("自动转发已停止")

    async def close(self):
        """关闭所有转发器"""
        for target_id, forwarder in list(self.forwarders.items()):
            try:
                if hasattr(forwarder, 'close'):
                    await forwarder.close()
            except Exception as e:
                logger.error(f"关闭转发器 {target_id} 失败: {e}")

        self.forwarders.clear()
        self.transformers.clear()
        self.target_systems.clear()
        self.forwarder_errors.clear()
        logger.info("转发器管理器已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        targets_stats = {}
        for target_id, target in self.target_systems.items():
            protocol = target.protocol_type.value if isinstance(target.protocol_type, ProtocolType) else str(target.protocol_type)
            forwarder = self.forwarders.get(target_id)
            targets_stats[target_id] = {
                "id": target_id,
                "name": target.name,
                "protocol": protocol,
                "is_active": target.is_active,
                "has_forwarder": forwarder is not None,
                "last_error": self.forwarder_errors.get(target_id),
                "forwarder_stats": forwarder.get_stats() if forwarder and hasattr(forwarder, "get_stats") else None,
            }

        return {
            "total_targets": len(self.target_systems),
            "active_targets": sum(
                1 for ts in self.target_systems.values() if ts.is_active
            ),
            "total_forwarders": len(self.forwarders),
            "auto_forward_active": self._auto_forward_active,
            "supported_protocols": [p.value for p in ForwarderFactory.get_supported_protocols()],
            "targets": targets_stats,
        }
