"""
统计监控API
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.database import get_db
from app.core.gateway.manager import get_gateway_manager
from app.models.data_source import DataSource
from app.models.target_system import TargetSystem
from app.models.routing_rule import RoutingRule

router = APIRouter()


@router.get("/")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取系统统计信息"""
    # 查询system_statistics视图
    result = await db.execute(
        text("SELECT * FROM gateway.system_statistics")
    )
    stats = result.fetchone()

    if stats:
        return {
            "active_data_sources": stats[0],
            "active_target_systems": stats[1],
            "active_routing_rules": stats[2],
            "published_frame_schemas": stats[3],
            "messages_last_24h": stats[4],
            "successful_forwards_24h": stats[5],
            "failed_forwards_24h": stats[6],
        }

    return {
        "active_data_sources": 0,
        "active_target_systems": 0,
        "active_routing_rules": 0,
        "published_frame_schemas": 0,
        "messages_last_24h": 0,
        "successful_forwards_24h": 0,
        "failed_forwards_24h": 0,
    }


@router.get("/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取系统概览统计"""
    gateway_manager = get_gateway_manager()
    gateway_status = gateway_manager.get_status()

    # 数据源统计
    data_source_count = await db.scalar(select(func.count(DataSource.id)))
    active_data_source_count = await db.scalar(
        select(func.count(DataSource.id)).where(DataSource.is_active == True)
    )

    # 目标系统统计
    target_system_count = await db.scalar(select(func.count(TargetSystem.id)))
    active_target_system_count = await db.scalar(
        select(func.count(TargetSystem.id)).where(TargetSystem.is_active == True)
    )

    # 路由规则统计
    routing_rule_count = await db.scalar(select(func.count(RoutingRule.id)))
    published_routing_rule_count = await db.scalar(
        select(func.count(RoutingRule.id)).where(RoutingRule.is_published == True)
    )

    # 消息统计
    total_messages = await db.scalar(select(func.sum(DataSource.total_messages))) or 0
    total_sent = await db.scalar(select(func.sum(TargetSystem.total_forwarded))) or 0
    total_failed = await db.scalar(select(func.sum(TargetSystem.total_failed))) or 0

    return {
        "gateway": {
            "is_running": gateway_status["is_running"],
            "running_adapters": len([a for a in gateway_status["adapters"].values() if a.get("is_running")]),
            "total_adapters": len(gateway_status["adapters"]),
        },
        "data_sources": {
            "total": data_source_count,
            "active": active_data_source_count,
            "running": len(gateway_status["adapters"]),
        },
        "target_systems": {
            "total": target_system_count,
            "active": active_target_system_count,
            "registered": gateway_status["pipeline"].get("active_targets", 0),
        },
        "routing_rules": {
            "total": routing_rule_count,
            "published": published_routing_rule_count,
        },
        "messages": {
            "total_received": total_messages,
            "total_sent": total_sent,
            "total_failed": total_failed,
            "success_rate": round(total_sent / (total_sent + total_failed) * 100, 2) if (total_sent + total_failed) > 0 else 100,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/data-sources")
async def get_data_sources_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取所有数据源的统计信息"""
    gateway_manager = get_gateway_manager()
    gateway_status = gateway_manager.get_status()

    # 获取所有数据源
    result = await db.execute(select(DataSource))
    data_sources = result.scalars().all()

    stats = []
    for ds in data_sources:
        adapter_id = str(ds.id)
        adapter_stats = gateway_status["adapters"].get(adapter_id)
        is_running = adapter_stats is not None

        stats.append({
            "id": str(ds.id),
            "name": ds.name,
            "protocol_type": ds.protocol_type,
            "is_active": ds.is_active,
            "is_running": is_running,
            "total_messages": ds.total_messages,
            "last_message_at": ds.last_message_at.isoformat() if ds.last_message_at else None,
            "adapter_stats": adapter_stats if is_running else None,
        })

    return {
        "total": len(stats),
        "running": len([s for s in stats if s["is_running"]]),
        "data_sources": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/target-systems")
async def get_target_systems_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取所有目标系统的统计信息"""
    gateway_manager = get_gateway_manager()
    forwarder_stats = gateway_manager.data_pipeline.forwarder_manager.get_stats()

    # 获取所有目标系统
    result = await db.execute(select(TargetSystem))
    target_systems = result.scalars().all()

    stats = []
    for ts in target_systems:
        target_id_str = str(ts.id)
        is_registered = target_id_str in forwarder_stats.get("targets", {})
        target_stats = forwarder_stats.get("targets", {}).get(target_id_str)

        stats.append({
            "id": str(ts.id),
            "name": ts.name,
            "protocol_type": ts.protocol_type,
            "is_active": ts.is_active,
            "is_registered": is_registered,
            "total_sent": ts.total_forwarded,
            "total_failed": ts.total_failed,
            "success_rate": round(ts.total_forwarded / (ts.total_forwarded + ts.total_failed) * 100, 2) if (ts.total_forwarded + ts.total_failed) > 0 else 100,
            "last_sent_at": ts.last_forward_at.isoformat() if ts.last_forward_at else None,
            "forwarder_stats": target_stats if is_registered else None,
        })

    return {
        "total": len(stats),
        "registered": len([s for s in stats if s["is_registered"]]),
        "target_systems": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/routing")
async def get_routing_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则统计信息"""
    gateway_manager = get_gateway_manager()
    routing_stats = gateway_manager.data_pipeline.routing_engine.get_stats()

    # 获取所有路由规则
    result = await db.execute(select(RoutingRule))
    routing_rules = result.scalars().all()

    rules_stats = []
    for rule in routing_rules:
        rules_stats.append({
            "id": str(rule.id),
            "name": rule.name,
            "priority": rule.priority,
            "is_published": rule.is_published,
            "total_matched": rule.match_count,
            "last_matched_at": rule.last_match_at.isoformat() if rule.last_match_at else None,
        })

    return {
        "total": len(rules_stats),
        "published": len([r for r in rules_stats if r["is_published"]]),
        "routing_engine_stats": routing_stats,
        "rules": rules_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


__all__ = ["router"]
