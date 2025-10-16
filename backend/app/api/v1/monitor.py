"""
监控与日志API
提供系统健康、指标历史以及消息日志查询接口
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psutil
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.gateway.manager import get_gateway_manager
from app.db.database import get_db
from app.db.redis import redis_client
from app.models.data_source import DataSource
from app.models.message_log import MessageLog
from app.services.monitoring_service import get_monitoring_service

router = APIRouter()


def _log_to_entry(log: MessageLog) -> Dict[str, Optional[str]]:
    """将数据库消息日志转换为前端期望的结构"""
    return {
        "id": str(log.id),
        "message_id": log.message_id,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "source_protocol": log.source_protocol,
        "source_id": str(log.source_id) if log.source_id else None,
        "target_systems": log.target_systems or [],
        "processing_status": log.processing_status,
        "processing_time_ms": 0,
        "error_message": log.error_message,
        "data_size": log.raw_data_size or 0,
    }


async def _collect_system_health(db: AsyncSession) -> Dict[str, Any]:
    """聚合系统健康信息并记录资源快照"""
    settings = get_settings()
    gateway_manager = get_gateway_manager()
    monitoring_service = get_monitoring_service()

    gateway_status = "healthy" if gateway_manager.is_running else "warning"

    # 数据库健康检查
    try:
        await db.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception:  # pragma: no cover
        database_status = "critical"

    # Redis健康检查
    redis_status = "unknown"
    try:
        await redis_client.connect()
        if redis_client.client:
            await redis_client.client.ping()
        redis_status = "healthy"
    except Exception:  # pragma: no cover
        redis_status = "critical"

    overall = "healthy"
    if "critical" in {gateway_status, database_status, redis_status}:
        overall = "critical"
    elif "warning" in {gateway_status, database_status, redis_status}:
        overall = "warning"

    runtime_metrics = await monitoring_service.get_runtime_metrics()

    # 连接数量使用当前运行中的适配器数
    connection_count = sum(
        1 for adapter in gateway_manager.adapters.values()
        if getattr(adapter, "is_running", False)
    )

    # 系统资源使用率
    try:
        cpu_usage = psutil.cpu_percent(interval=None)
        if cpu_usage == 0.0:
            cpu_usage = psutil.cpu_percent(interval=0.05)
    except Exception:  # pragma: no cover - psutil不可用时返回0
        cpu_usage = 0.0

    try:
        memory_usage = psutil.virtual_memory().percent
    except Exception:  # pragma: no cover
        memory_usage = 0.0

    disk_path = getattr(settings, "MONITOR_DISK_PATH", "/")
    try:
        disk_usage = psutil.disk_usage(disk_path).percent
    except Exception:  # pragma: no cover
        try:
            disk_usage = psutil.disk_usage("/").percent
        except Exception:
            disk_usage = 0.0

    # 记录系统快照到监控历史
    await monitoring_service.record_system_metrics(
        timestamp=datetime.utcnow(),
        cpu_usage=float(cpu_usage),
        memory_usage=float(memory_usage),
        disk_usage=float(disk_usage),
        message_rate=runtime_metrics["messages_per_second"],
        error_rate=runtime_metrics["error_rate"],
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall": overall,
        "services": {
            "gateway": gateway_status,
            "database": database_status,
            "redis": redis_status,
        },
        "metrics": {
            "cpu_usage": float(cpu_usage),
            "memory_usage": float(memory_usage),
            "disk_usage": float(disk_usage),
            "connection_count": connection_count,
            "message_rate": runtime_metrics["messages_per_second"],
            "error_rate": runtime_metrics["error_rate"],
        },
    }


@router.get("/logs")
async def get_recent_logs(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取最近的消息处理日志"""
    total = await db.scalar(select(func.count(MessageLog.id)))

    result = await db.execute(
        select(MessageLog).order_by(desc(MessageLog.timestamp)).limit(limit)
    )
    logs = result.scalars().all()

    return {
        "items": [_log_to_entry(log) for log in logs],
        "total": total or 0,
        "limit": limit,
    }


@router.get("/metrics")
async def get_metrics_history(
    time_range: str = Query("1h", alias="timeRange"),
    metrics: Optional[List[str]] = Query(None),
):
    """获取历史指标数据"""
    del metrics  # 当前版本未按指标字段筛选

    time_range_map = {
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "6h": 360,
        "12h": 720,
        "24h": 1440,
    }
    minutes = time_range_map.get(time_range.lower(), 60)

    monitoring_service = get_monitoring_service()
    history = await monitoring_service.get_metrics_history(minutes)

    return history


@router.get("/health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
):
    """获取系统健康状态和关键指标"""
    return await _collect_system_health(db)


@router.get("/dashboard")
async def get_dashboard_snapshot(
    db: AsyncSession = Depends(get_db),
):
    """获取仪表板聚合数据"""
    monitoring_service = get_monitoring_service()
    system_health = await _collect_system_health(db)
    metrics_history = await monitoring_service.get_metrics_history(24 * 60)

    overview = await _build_overview(db, system_health, metrics_history)
    protocol_stats = await _build_protocol_distribution(db)
    traffic_data, performance_metrics = _build_dashboard_timeseries(metrics_history)
    alerts = await _fetch_recent_alerts(db)
    recent_activities = await _fetch_recent_activities(db)

    return {
        "overview": overview,
        "protocolStats": protocol_stats,
        "trafficData": traffic_data,
        "performanceMetrics": performance_metrics,
        "systemHealth": system_health,
        "alerts": alerts,
        "recentActivities": recent_activities,
    }


def _percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100.0, 2)


async def _build_overview(
    db: AsyncSession,
    system_health: Dict[str, Any],
    metrics_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = datetime.utcnow()
    last_hour_start = now - timedelta(hours=1)
    previous_hour_start = now - timedelta(hours=2)
    last_day_start = now - timedelta(hours=24)

    last_hour = _sum_history(metrics_history, last_hour_start, now)
    previous_hour = _sum_history(metrics_history, previous_hour_start, last_hour_start)
    last_day = _sum_history(metrics_history, last_day_start, now)

    # 数据传输量（基于日志原始数据大小统计）
    transfer_start = now - timedelta(hours=24)
    total_bytes = await db.scalar(
        select(func.coalesce(func.sum(MessageLog.raw_data_size), 0))
        .where(MessageLog.timestamp >= transfer_start)
    )
    data_transfer_mb = round(float(total_bytes or 0) / (1024 * 1024), 2)

    success_rate = (
        (last_hour["success"] / last_hour["received"]) * 100.0
        if last_hour["received"]
        else 100.0
    )
    previous_success_rate = (
        (previous_hour["success"] / previous_hour["received"]) * 100.0
        if previous_hour["received"]
        else 100.0
    )

    error_count = last_day["failed"]
    overview_trends = {
        "connections": 0.0,
        "dataTransfer": _percent_change(last_hour["received"], previous_hour["received"]),
        "successRate": round(success_rate - previous_success_rate, 2),
        "errors": _percent_change(last_hour["failed"], previous_hour["failed"]),
    }

    return {
        "totalConnections": system_health["metrics"]["connection_count"],
        "dataTransfer": data_transfer_mb,
        "successRate": round(success_rate, 2),
        "errorCount": error_count,
        "trends": overview_trends,
    }


async def _build_protocol_distribution(db: AsyncSession) -> List[Dict[str, Any]]:
    color_palette = [
        "#1890ff",
        "#52c41a",
        "#faad14",
        "#f5222d",
        "#722ed1",
        "#13c2c2",
        "#eb2f96",
    ]

    result = await db.execute(
        select(DataSource.protocol_type, func.count(DataSource.id))
        .group_by(DataSource.protocol_type)
        .order_by(func.count(DataSource.id).desc())
    )
    records = result.all()

    stats: List[Dict[str, Any]] = []
    for index, (protocol, count) in enumerate(records):
        name = str(protocol or "UNKNOWN").upper()
        color = color_palette[index % len(color_palette)]
        stats.append({"name": name, "value": int(count or 0), "color": color})

    if not stats:
        stats = [
            {"name": "HTTP", "value": 0, "color": color_palette[0]},
            {"name": "MQTT", "value": 0, "color": color_palette[1]},
        ]

    return stats


def _build_dashboard_timeseries(
    metrics_history: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    now = datetime.utcnow()
    traffic_bucket: Dict[datetime, Dict[str, float]] = defaultdict(
        lambda: {"received": 0.0, "success": 0.0, "failed": 0.0, "message_rate_sum": 0.0, "error_rate_sum": 0.0, "samples": 0}
    )

    for entry in metrics_history:
        ts = datetime.fromisoformat(entry["timestamp"])
        if ts < now - timedelta(hours=24):
            continue
        metrics = entry.get("metrics", {})
        bucket_key = ts.replace(minute=0, second=0, microsecond=0)
        bucket = traffic_bucket[bucket_key]
        bucket["received"] += metrics.get("received", 0)
        bucket["success"] += metrics.get("success", 0)
        bucket["failed"] += metrics.get("failed", 0)
        bucket["message_rate_sum"] += metrics.get("message_rate", 0.0)
        bucket["error_rate_sum"] += metrics.get("error_rate", 0.0)
        bucket["samples"] += 1

    sorted_hours = sorted(traffic_bucket.keys())

    traffic_data: List[Dict[str, Any]] = []
    for hour in sorted_hours[-24:]:
        bucket = traffic_bucket[hour]
        inbound = int(bucket["received"])
        outbound = int(bucket["success"])
        traffic_data.append({
            "time": hour.strftime("%H:%M"),
            "inbound": inbound,
            "outbound": outbound,
            "total": inbound + outbound,
        })

    performance_data: List[Dict[str, Any]] = []
    for hour in sorted_hours[-12:]:
        bucket = traffic_bucket[hour]
        message_rate_avg = (
            bucket["message_rate_sum"] / bucket["samples"] if bucket["samples"] else 0.0
        )
        error_rate_percent = (
            (bucket["failed"] / bucket["received"]) * 100.0
            if bucket["received"]
            else bucket["error_rate_sum"] / bucket["samples"] * 100.0
            if bucket["samples"]
            else 0.0
        )
        throughput = bucket["success"]
        latency = max(1.0, 1000.0 / max(message_rate_avg, 0.1))

        performance_data.append({
            "hour": hour.strftime("%H:%M"),
            "throughput": round(throughput, 2),
            "latency": round(latency, 2),
            "errorRate": round(error_rate_percent, 2),
        })

    return traffic_data, performance_data


async def _fetch_recent_alerts(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(MessageLog)
        .where(MessageLog.error_message.isnot(None))
        .order_by(desc(MessageLog.timestamp))
        .limit(5)
    )
    alerts = []
    for log in result.scalars():
        alerts.append({
            "id": str(log.id),
            "level": "critical",
            "message": log.error_message or "转发异常",
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "source": log.source_protocol or "gateway",
        })
    return alerts


async def _fetch_recent_activities(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(MessageLog)
        .order_by(desc(MessageLog.timestamp))
        .limit(10)
    )
    activities = []
    for log in result.scalars():
        status = (log.processing_status or "").lower()
        activity_type = "error" if status in {"failed"} or log.error_message else "message"
        description_parts = [log.source_protocol or "UNKNOWN"]
        if log.message_id:
            description_parts.append(f"消息 {log.message_id}")
        description_parts.append(f"状态 {status or 'unknown'}")

        activities.append({
            "id": str(log.id),
            "type": activity_type,
            "description": " · ".join(description_parts),
            "user": "系统",
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
        })
    return activities


def _sum_history(
    history: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
) -> Dict[str, float]:
    totals = {
        "received": 0.0,
        "success": 0.0,
        "failed": 0.0,
        "message_rate": 0.0,
        "error_rate": 0.0,
        "samples": 0,
    }
    for entry in history:
        ts = datetime.fromisoformat(entry["timestamp"])
        if ts < start or ts >= end:
            continue
        metrics = entry.get("metrics", {})
        totals["received"] += metrics.get("received", 0)
        totals["success"] += metrics.get("success", 0)
        totals["failed"] += metrics.get("failed", 0)
        totals["message_rate"] += metrics.get("message_rate", 0.0)
        totals["error_rate"] += metrics.get("error_rate", 0.0)
        totals["samples"] += 1
    return totals


__all__ = ["router"]
