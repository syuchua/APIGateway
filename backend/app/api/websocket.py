"""
WebSocket实时推送API
用于向前端推送实时监控数据和日志
"""
import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Set
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func, desc

from app.core.gateway.manager import get_gateway_manager
from app.db.database import AsyncSessionLocal
from app.models.data_source import DataSource
from app.models.target_system import TargetSystem
from app.models.routing_rule import RoutingRule
from app.models.message_log import MessageLog
from app.schemas.websocket import (
    create_monitor_message,
    create_log_message,
    create_error_message,
    MonitorData,
)
from app.services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)

# 内存日志缓冲区（最多保存最近1000条日志）
log_buffer = deque(maxlen=1000)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 监控数据订阅者
        self.monitor_connections: Set[WebSocket] = set()
        # 日志订阅者
        self.log_connections: Set[WebSocket] = set()
        # 消息数据订阅者
        self.message_connections: Set[WebSocket] = set()

    async def connect_monitor(self, websocket: WebSocket):
        """连接监控推送"""
        await websocket.accept()
        self.monitor_connections.add(websocket)
        logger.info(f"监控WebSocket连接: {websocket.client}")

    async def connect_logs(self, websocket: WebSocket):
        """连接日志推送"""
        await websocket.accept()
        self.log_connections.add(websocket)
        logger.info(f"日志WebSocket连接: {websocket.client}")

    async def connect_messages(self, websocket: WebSocket):
        """连接消息推送"""
        await websocket.accept()
        self.message_connections.add(websocket)
        logger.info(f"消息WebSocket连接: {websocket.client}")

    def disconnect_monitor(self, websocket: WebSocket):
        """断开监控连接"""
        self.monitor_connections.discard(websocket)
        logger.info(f"监控WebSocket断开: {websocket.client}")

    def disconnect_logs(self, websocket: WebSocket):
        """断开日志连接"""
        self.log_connections.discard(websocket)
        logger.info(f"日志WebSocket断开: {websocket.client}")

    def disconnect_messages(self, websocket: WebSocket):
        """断开消息连接"""
        self.message_connections.discard(websocket)
        logger.info(f"消息WebSocket断开: {websocket.client}")

    async def broadcast_monitor(self, data: dict):
        """广播监控数据"""
        disconnected = set()
        for connection in self.monitor_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"发送监控数据失败: {e}")
                disconnected.add(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.monitor_connections.discard(conn)

    async def broadcast_log(self, log_data: dict):
        """广播日志"""
        disconnected = set()
        for connection in self.log_connections:
            try:
                await connection.send_json(log_data)
            except Exception as e:
                logger.error(f"发送日志失败: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.log_connections.discard(conn)

    async def broadcast_message(self, message_data: dict):
        """广播消息数据"""
        disconnected = set()
        for connection in self.message_connections:
            try:
                await connection.send_json(message_data)
            except Exception as e:
                logger.error(f"发送消息数据失败: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.message_connections.discard(conn)


# 全局连接管理器
manager = ConnectionManager()


async def websocket_monitor_endpoint(websocket: WebSocket):
    """
    监控数据WebSocket端点
    推送实时性能指标和系统状态
    """
    await manager.connect_monitor(websocket)

    try:
        # 启动定时推送任务
        push_task = asyncio.create_task(push_monitor_data(websocket))

        # 接收客户端消息（可用于控制推送频率等）
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理客户端命令
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break

    finally:
        push_task.cancel()
        manager.disconnect_monitor(websocket)


async def websocket_data_source_endpoint(websocket: WebSocket, data_source_id: UUID):
    """为 WebSocket 数据源提供的测试入口。"""

    gateway_manager = get_gateway_manager()

    adapter = gateway_manager.adapters.get(str(data_source_id))
    if adapter is None or not hasattr(adapter, "receive_message"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not gateway_manager.is_running:
        await gateway_manager.start()

    await websocket.accept()

    connection_id = str(uuid4())
    client_addr = (
        f"{websocket.client.host}:{websocket.client.port}"
        if websocket.client else "unknown"
    )

    try:
        if hasattr(adapter, "add_connection"):
            await adapter.add_connection(connection_id, client_addr)

        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if message.get("type") == "websocket.disconnect":
                break

            payload = message.get("text") if message.get("text") is not None else message.get("bytes")
            await adapter.receive_message(connection_id, payload, client_addr)  # type: ignore[attr-defined]

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("数据源 WebSocket 处理失败: %s", exc, exc_info=True)
    finally:
        if hasattr(adapter, "remove_connection"):
            await adapter.remove_connection(connection_id)
        try:
            await websocket.close()
        except Exception:  # pragma: no cover
            pass


async def push_monitor_data(websocket: WebSocket):
    """定时推送监控数据"""
    # 缓存数据库统计，每10秒更新一次（减少数据库查询频率）
    db_stats_cache = {"data_sources": 0, "target_systems": 0, "routing_rules": 0, "last_update": 0}

    while True:
        try:
            # 获取网关状态
            gateway_manager = get_gateway_manager()
            gateway_status = gateway_manager.get_status()
            monitoring_service = get_monitoring_service()
            runtime_metrics = await monitoring_service.get_runtime_metrics()

            # 每10秒更新一次数据库统计（避免频繁查询）
            current_time = asyncio.get_event_loop().time()
            if current_time - db_stats_cache["last_update"] > 10:
                try:
                    async with AsyncSessionLocal() as db:
                        data_source_count = await db.scalar(select(func.count(DataSource.id))) or 0
                        target_system_count = await db.scalar(select(func.count(TargetSystem.id))) or 0
                        routing_rule_count = await db.scalar(select(func.count(RoutingRule.id))) or 0

                        db_stats_cache.update({
                            "data_sources": data_source_count,
                            "target_systems": target_system_count,
                            "routing_rules": routing_rule_count,
                            "last_update": current_time
                        })
                except Exception as db_error:
                    logger.warning(f"获取数据库统计失败: {db_error}")

            # 统计运行中的适配器
            running_adapters = len([
                a for a in gateway_status.get("adapters", {}).values()
                if a.get("is_running")
            ])
            total_adapters = len(gateway_status.get("adapters", {}))
            pipeline_stats = gateway_status.get("pipeline", {})
            forwarder_stats = pipeline_stats.get("forwarder_stats", {})
            forwarders_active = forwarder_stats.get("total_forwarders", 0)

            # 使用新的WebSocket消息格式
            monitor_data = MonitorData(
                gateway_status="running" if gateway_status.get("is_running") else "stopped",
                adapters_running=running_adapters,
                adapters_total=total_adapters,
                forwarders_active=forwarders_active,
                messages_per_second=runtime_metrics["messages_per_second"],
                messages_total=runtime_metrics["messages_total"],
                error_rate=runtime_metrics["error_rate"],
                cpu_usage=None,  # 可选
                memory_usage=None,  # 可选
            )

            # 创建标准格式的监控消息
            message = create_monitor_message(monitor_data)

            # 发送数据
            await websocket.send_json(message)

            # 每2秒推送一次
            await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info("监控数据推送任务已取消")
            break
        except Exception as e:
            logger.error(f"推送监控数据失败: {e}")
            # 发送错误消息
            try:
                error_msg = create_error_message(
                    error="监控数据推送失败",
                    detail=str(e)
                )
                await websocket.send_json(error_msg)
            except:
                pass
            await asyncio.sleep(2)


async def websocket_logs_endpoint(websocket: WebSocket):
    """
    日志WebSocket端点
    推送实时日志流
    """
    await manager.connect_logs(websocket)
    push_task = None

    try:
        # 发送欢迎消息
        welcome_msg = create_log_message(
            level="info",
            message="日志WebSocket连接成功，等待日志数据...",
            source="system",
            extra={"status": "connected"}
        )
        await websocket.send_json(welcome_msg)

        # 发送历史日志（最近50条）
        try:
            async with AsyncSessionLocal() as db:
                recent_logs = await db.execute(
                    select(MessageLog)
                    .order_by(desc(MessageLog.timestamp))
                    .limit(50)
                )
                logs = recent_logs.scalars().all()

                if logs:
                    logger.info(f"发送 {len(logs)} 条历史日志")
                    for log in reversed(logs):  # 按时间顺序发送
                        log_msg = create_log_message(
                            level="info" if log.processing_status == "success" else "error",
                            message=f"[{log.source_protocol}] {log.message_id}",
                            source="gateway",
                            extra={
                                "id": str(log.id),
                                "source_protocol": log.source_protocol,
                                "processing_status": log.processing_status,
                                "error": log.error_message
                            }
                        )
                        await websocket.send_json(log_msg)
                else:
                    logger.info("数据库中暂无历史日志")
                    # 发送提示消息
                    no_logs_msg = create_log_message(
                        level="info",
                        message="暂无历史日志数据",
                        source="system",
                        extra={"status": "no_logs"}
                    )
                    await websocket.send_json(no_logs_msg)
        except Exception as e:
            logger.warning(f"发送历史日志失败: {e}")
            # 即使失败也继续运行

        # 启动实时推送任务
        push_task = asyncio.create_task(push_log_data(websocket))

        # 接收客户端消息（可用于过滤日志等）
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理客户端命令
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

            except WebSocketDisconnect:
                logger.info(f"日志WebSocket客户端主动断开")
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break

    except Exception as e:
        logger.error(f"日志WebSocket异常: {e}")
    finally:
        if push_task and not push_task.done():
            push_task.cancel()
            try:
                await push_task
            except asyncio.CancelledError:
                pass
        manager.disconnect_logs(websocket)


async def push_log_data(websocket: WebSocket):
    """定时推送日志数据"""
    last_log_id = None

    while True:
        try:
            # 从数据库获取新日志（每5秒查询一次）
            async with AsyncSessionLocal() as db:
                query = select(MessageLog).order_by(desc(MessageLog.timestamp)).limit(10)

                if last_log_id:
                    # 只获取比上次更新的日志
                    query = query.where(MessageLog.id > last_log_id)

                result = await db.execute(query)
                logs = result.scalars().all()

                if logs:
                    last_log_id = logs[0].id

                    for log in reversed(logs):  # 按时间顺序发送
                        log_msg = create_log_message(
                            level="info" if log.processing_status == "success" else "error",
                            message=f"[{log.source_protocol}] {log.message_id}",
                            source="gateway",
                            extra={
                                "id": str(log.id),
                                "source_protocol": log.source_protocol,
                                "processing_status": log.processing_status,
                                "raw_data_size": log.raw_data_size,
                                "error": log.error_message
                            }
                        )
                        await websocket.send_json(log_msg)

                        # 同时添加到内存缓冲区
                        log_buffer.append(log_msg)

            # 每5秒查询一次
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("日志推送任务已取消")
            break
        except Exception as e:
            logger.error(f"推送日志数据失败: {e}")
            await asyncio.sleep(5)


async def websocket_messages_endpoint(websocket: WebSocket):
    """
    消息数据WebSocket端点
    推送实时接收和转发的消息
    """
    await manager.connect_messages(websocket)

    try:
        # 接收客户端消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理客户端命令
                if message.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break

    finally:
        manager.disconnect_messages(websocket)


def get_connection_manager() -> ConnectionManager:
    """获取全局连接管理器"""
    return manager


__all__ = [
    "websocket_monitor_endpoint",
    "websocket_logs_endpoint",
    "websocket_messages_endpoint",
    "websocket_data_source_endpoint",
    "get_connection_manager",
]
