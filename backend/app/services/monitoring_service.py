"""
网关监控与日志服务
负责将管道处理的消息写入数据库日志，并维护实时监控数据
"""
import asyncio
import logging
from collections import deque, OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.core.eventbus import SimpleEventBus, get_eventbus
from app.db.database import AsyncSessionLocal
from app.models.message_log import MessageLog
from app.repositories.data_source import DataSourceRepository
from app.repositories.routing_rule import RoutingRuleRepository
from app.repositories.target_system import TargetSystemRepository
from app.schemas.forwarder import ForwardStatus
from app.schemas.common import ProtocolType

logger = logging.getLogger(__name__)


class GatewayMonitoringService:
    """集中处理网关监控指标和消息日志"""

    _history_window_minutes = 24 * 60  # 24小时
    _recent_window_seconds = 60  # 1分钟窗口用于速率统计

    def __init__(self, eventbus: SimpleEventBus):
        self.eventbus = eventbus
        self._lock = asyncio.Lock()

        # 消息追踪：message_id -> {log_id, minute, created_at}
        self._message_index: Dict[str, Dict[str, Any]] = {}

        # 统计数据
        self._total_messages = 0
        self._success_messages = 0
        self._failed_messages = 0

        self._recent_messages: deque[float] = deque()
        self._recent_failures: deque[float] = deque()

        # 历史指标（分钟粒度）
        self._history_order: deque[datetime] = deque()
        self._history: "OrderedDict[datetime, Dict[str, int]]" = OrderedDict()

        # 系统资源指标历史
        self._system_history_order: deque[datetime] = deque()
        self._system_history: "OrderedDict[datetime, Dict[str, float]]" = OrderedDict()

    async def record_routing_decision(self, routing_result: Dict[str, Any]) -> None:
        """
        记录路由决策结果，生成初始日志
        """
        message_id = routing_result.get("message_id")
        if not message_id:
            logger.debug("routing_result 缺少 message_id，跳过日志记录")
            return

        log_id = uuid4()
        now = self._to_naive(datetime.utcnow())
        now = now.replace(microsecond=int(now.microsecond / 1000) * 1000)
        minute_slot = now.replace(second=0, microsecond=0)

        source_protocol = self._normalize_protocol(routing_result.get("source_protocol"))

        source_id_raw = routing_result.get("data_source_id")
        source_id: Optional[UUID] = None
        if source_id_raw:
            try:
                source_id = UUID(str(source_id_raw))
            except (ValueError, TypeError):
                logger.debug("无法将 data_source_id 转换为UUID: %s", source_id_raw)

        raw_data = routing_result.get("raw_data")
        raw_bytes: Optional[bytes] = None
        if isinstance(raw_data, (bytes, bytearray)):
            raw_bytes = bytes(raw_data)
        elif isinstance(raw_data, str):
            raw_bytes = raw_data.encode("utf-8")

        raw_size = routing_result.get("data_size")
        if raw_size is None and raw_bytes is not None:
            raw_size = len(raw_bytes)

        status = "awaiting_forward"
        if not routing_result.get("target_system_ids"):
            status = "no_target"

        inserted = False
        matched_rules = routing_result.get("matched_rules") or []
        for attempt in range(2):
            try:
                async with AsyncSessionLocal() as session:
                    await self._ensure_partition(session, now)
                    session.add(
                        MessageLog(
                            id=log_id,
                            timestamp=now,
                            message_id=message_id,
                            source_protocol=source_protocol,
                            source_id=source_id,
                            source_address=routing_result.get("source_address"),
                            raw_data=raw_bytes,
                            raw_data_size=raw_size,
                            parsed_data=routing_result.get("parsed_data"),
                            processing_status=status,
                            matched_rules=matched_rules,
                            target_systems=routing_result.get("target_system_ids"),
                            error_message=None,
                        )
                    )

                    if source_id:
                        try:
                            repo = DataSourceRepository(session)
                            await repo.increment_message_count(source_id)
                        except Exception as exc:  # pragma: no cover - 统计失败不影响主流程
                            logger.warning("更新数据源统计失败: %s", exc, exc_info=True)

                    if matched_rules:
                        rule_repo = RoutingRuleRepository(session)
                        for rule in matched_rules:
                            rule_id = rule.get("rule_id")
                            if not rule_id:
                                continue
                            try:
                                await rule_repo.increment_match_count(UUID(str(rule_id)))
                            except Exception as exc:  # pragma: no cover
                                logger.warning("更新路由规则统计失败: %s", exc, exc_info=True)

                    await session.commit()
                    inserted = True
                    break
            except IntegrityError as exc:
                logger.error("写入消息日志失败: %s", exc, exc_info=True)
                if "no partition" in str(exc).lower() and attempt == 0:
                    continue
                break
            except Exception as exc:
                logger.error("写入消息日志失败: %s", exc, exc_info=True)
                break

        if not inserted:
            log_id = None

        timestamp = now.timestamp()

        async with self._lock:
            self._total_messages += 1
            self._recent_messages.append(timestamp)
            self._prune_recent(timestamp)

            if minute_slot not in self._history:
                self._history[minute_slot] = {"received": 0, "success": 0, "failed": 0}
                self._history_order.append(minute_slot)
                self._trim_history()

            self._history[minute_slot]["received"] += 1

            if log_id is not None:
                self._message_index[message_id] = {
                    "log_id": log_id,
                    "minute": minute_slot,
                    "created_at": now,
                }

    async def record_forward_results(
        self,
        message: Dict[str, Any],
        forward_results: List[Dict[str, Any]],
    ) -> None:
        """
        在转发结束后更新日志记录以及统计信息
        """
        message_id = message.get("message_id")
        if not message_id:
            logger.debug("forward_results 缺少 message_id，跳过")
            return

        ts_now = self._to_naive(datetime.utcnow())
        timestamp = ts_now.timestamp()

        log_id: Optional[UUID] = None
        minute_slot: Optional[datetime] = None

        async with self._lock:
            index_entry = self._message_index.get(message_id)
            if index_entry:
                log_id = index_entry.get("log_id")
                minute_slot = index_entry.get("minute")
                created_at = self._to_naive(index_entry.get("created_at")) if index_entry.get("created_at") else None
            else:
                created_at = None
            self._cleanup_index(ts_now)

        success_count = 0
        failure_count = 0
        target_ids: List[str] = []
        errors: List[str] = []

        forward_status_map: Dict[str, str] = {}

        for result in forward_results or []:
            status = result.get("status")
            if isinstance(status, ForwardStatus):
                status_value = status.value
            else:
                status_value = str(status).lower()

            target_id_value = result.get("target_id") or result.get("target_id".upper())
            if target_id_value:
                target_id_str = str(target_id_value)
                target_ids.append(target_id_str)
                forward_status_map[target_id_str] = status_value

            if status_value == ForwardStatus.SUCCESS.value:
                success_count += 1
            else:
                failure_count += 1
                if result.get("error"):
                    errors.append(str(result["error"]))

        if not forward_results:
            status_text = "no_target"
        elif failure_count == 0:
            status_text = "success"
        elif success_count == 0:
            status_text = "failed"
        else:
            status_text = "partial_success"

        target_ids = list(dict.fromkeys(target_ids))
        error_message = "; ".join(errors) if errors else None

        if log_id is None:
            # 未找到先前的路由记录，补写一条日志
            log_id = uuid4()
            minute_slot = ts_now.replace(second=0, microsecond=0)
            created_at = ts_now

        try:
            async with AsyncSessionLocal() as session:
                try:
                    if log_id is not None and created_at is not None:
                        created_at = self._to_naive(created_at)
                        try:
                            log_record = await session.get(MessageLog, (log_id, created_at))
                        except InvalidRequestError:
                            log_record = None
                    else:
                        log_record = None
                    if log_record is None:
                        await self._ensure_partition(session, ts_now)
                        log_record = MessageLog(
                            id=log_id,
                            timestamp=ts_now,
                            message_id=message_id,
                            source_protocol=self._normalize_protocol(message.get("source_protocol")),
                            source_id=None,
                        )
                        session.add(log_record)

                    log_record.processing_status = status_text
                    log_record.target_systems = target_ids or log_record.target_systems
                    log_record.error_message = error_message
                    log_record.raw_data_size = (
                        log_record.raw_data_size or message.get("data_size")
                    )

                    if forward_status_map:
                        target_repo = TargetSystemRepository(session)
                        for target_id_str, status_value in forward_status_map.items():
                            try:
                                await target_repo.increment_forward_count(
                                    UUID(target_id_str),
                                    success=status_value == ForwardStatus.SUCCESS.value,
                                )
                            except Exception as exc:  # pragma: no cover
                                logger.warning("更新目标系统统计失败: %s", exc, exc_info=True)

                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        except Exception as exc:  # pragma: no cover - 记录失败不影响主流程
            logger.error("更新消息日志失败: %s", exc, exc_info=True)
            try:
                await session.rollback()
            except Exception:  # pragma: no cover
                pass

        async with self._lock:
            if status_text == "success":
                self._success_messages += 1
            elif status_text == "failed":
                self._failed_messages += 1
                self._recent_failures.append(timestamp)
            elif status_text == "partial_success":
                self._recent_failures.append(timestamp)

            self._prune_recent(timestamp)

            slot = minute_slot or ts_now.replace(second=0, microsecond=0)
            if slot not in self._history:
                self._history[slot] = {"received": 0, "success": 0, "failed": 0}
                self._history_order.append(slot)
                self._trim_history()

            if status_text == "success":
                self._history[slot]["success"] += 1
            elif status_text in {"failed", "partial_success"}:
                self._history[slot]["failed"] += 1

            self._message_index.pop(message_id, None)

    async def get_runtime_metrics(self) -> Dict[str, Any]:
        """获取实时统计指标"""
        async with self._lock:
            now_ts = datetime.utcnow().timestamp()
            self._prune_recent(now_ts)

            recent_count = len(self._recent_messages)
            failure_count = len(self._recent_failures)

            messages_per_second = (
                recent_count / self._recent_window_seconds
                if self._recent_window_seconds
                else 0.0
            )
            error_rate = (failure_count / recent_count) if recent_count else 0.0

            return {
                "messages_total": self._total_messages,
                "messages_per_second": round(messages_per_second, 4),
                "error_rate": round(error_rate, 4),
                "success_messages": self._success_messages,
                "failed_messages": self._failed_messages,
            }

    async def get_metrics_history(self, minutes: int) -> List[Dict[str, Any]]:
        """获取指定时间范围内的历史指标"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        async with self._lock:
            slots = {
                slot for slot in self._history_order if slot >= cutoff
            } | {
                slot for slot in self._system_history_order if slot >= cutoff
            }

            data: List[Dict[str, Any]] = []
            for slot in sorted(slots):
                stats = self._history.get(slot, {})
                system_stats = self._system_history.get(slot, {})
                data.append({
                    "timestamp": slot.isoformat(),
                    "metrics": {
                        "received": stats.get("received", 0),
                        "success": stats.get("success", 0),
                        "failed": stats.get("failed", 0),
                        "cpu_usage": system_stats.get("cpu_usage", 0.0),
                        "memory_usage": system_stats.get("memory_usage", 0.0),
                        "disk_usage": system_stats.get("disk_usage", 0.0),
                        "message_rate": system_stats.get("message_rate", 0.0),
                        "error_rate": system_stats.get("error_rate", 0.0),
                    }
                })
            return data

    async def reset(self) -> None:
        """测试用重置"""
        async with self._lock:
            self._message_index.clear()
            self._total_messages = 0
            self._success_messages = 0
            self._failed_messages = 0
            self._recent_messages.clear()
            self._recent_failures.clear()
            self._history_order.clear()
            self._history.clear()
            self._system_history_order.clear()
            self._system_history.clear()

    def _prune_recent(self, current_ts: float) -> None:
        """移除超过窗口期的实时记录"""
        threshold = current_ts - self._recent_window_seconds
        while self._recent_messages and self._recent_messages[0] < threshold:
            self._recent_messages.popleft()
        while self._recent_failures and self._recent_failures[0] < threshold:
            self._recent_failures.popleft()

    def _trim_history(self) -> None:
        """保持历史记录窗口大小"""
        while len(self._history_order) > self._history_window_minutes:
            slot = self._history_order.popleft()
            self._history.pop(slot, None)
        self._trim_system_history()

    def _trim_system_history(self) -> None:
        """保持系统指标历史窗口大小"""
        while len(self._system_history_order) > self._history_window_minutes:
            slot = self._system_history_order.popleft()
            self._system_history.pop(slot, None)

    def _cleanup_index(self, now: datetime) -> None:
        """移除长时间未更新的索引信息"""
        threshold = now - timedelta(minutes=5)
        stale_keys = [
            mid for mid, meta in self._message_index.items()
            if (created_at := self._to_naive(meta.get("created_at"))) and created_at < threshold
        ]
        for mid in stale_keys:
            self._message_index.pop(mid, None)

    async def record_system_metrics(
        self,
        *,
        timestamp: datetime,
        cpu_usage: float,
        memory_usage: float,
        disk_usage: float,
        message_rate: float,
        error_rate: float,
    ) -> None:
        """记录系统资源与运行指标快照"""
        minute_slot = timestamp.replace(second=0, microsecond=0)
        async with self._lock:
            self._system_history[minute_slot] = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "message_rate": message_rate,
                "error_rate": error_rate,
            }
            self._system_history_order.append(minute_slot)
            self._trim_system_history()

    @staticmethod
    def _to_naive(value: Optional[datetime]) -> Optional[datetime]:
        """确保datetime为UTC无时区的naive值"""
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    async def _ensure_partition(self, session, timestamp: datetime) -> None:
        """确保对应月份的日志分区存在"""
        month_start = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)

        partition_name = f"message_logs_{month_start.year}_{month_start.month:02d}"
        start_str = month_start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = next_month.strftime("%Y-%m-%d %H:%M:%S")

        sql = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = '{partition_name}' AND n.nspname = 'gateway'
            ) THEN
                EXECUTE format(
                    'CREATE TABLE gateway.%I PARTITION OF gateway.message_logs FOR VALUES FROM (%L) TO (%L)',
                    '{partition_name}',
                    '{start_str}',
                    '{end_str}'
                );
            END IF;
        END;
        $$;
        """

        await session.execute(text(sql))

    def _normalize_protocol(self, value: Any) -> str:
        """将协议值规范为数据库可存储的短字符串"""
        if isinstance(value, ProtocolType):
            return value.value
        if value is None:
            return "UNKNOWN"
        text = str(value)
        if text.startswith("ProtocolType."):
            text = text.split(".", 1)[1]
        return text.upper()[:20]


_monitoring_service: Optional[GatewayMonitoringService] = None


def get_monitoring_service(eventbus: Optional[SimpleEventBus] = None) -> GatewayMonitoringService:
    """获取全局监控服务实例"""
    global _monitoring_service
    if _monitoring_service is None:
        eventbus = eventbus or get_eventbus()
        _monitoring_service = GatewayMonitoringService(eventbus)
    return _monitoring_service


__all__ = ["GatewayMonitoringService", "get_monitoring_service"]
