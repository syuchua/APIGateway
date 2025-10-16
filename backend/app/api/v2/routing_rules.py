"""
路由规则管理API v2 - 简化响应格式
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.routing_rule import RoutingRuleRepository
from app.core.gateway.manager import get_gateway_manager
from app.schemas.routing_rule_simple import RoutingRuleSimpleResponse
from app.schemas.routing_rule import (
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
)
from app.schemas.response import success_response, error_response, paginated_response
from app.models.routing_rule import RoutingRule

router = APIRouter()
logger = logging.getLogger(__name__)


def _model_to_simple_response(rule: RoutingRule) -> RoutingRuleSimpleResponse:
    """将ORM模型转换为简化响应Schema"""
    # 从target_systems数组提取ID列表
    target_system_ids = []
    if rule.target_systems:
        for ts in rule.target_systems:
            if isinstance(ts, dict) and "id" in ts:
                target_system_ids.append(str(ts["id"]))

    # 从source_config提取source_pattern
    source_pattern = None
    if rule.source_config and isinstance(rule.source_config, dict):
        # 尝试多种可能的字段名
        source_pattern = (
            rule.source_config.get("source_pattern") or
            rule.source_config.get("protocol_types") or
            rule.source_config.get("data_source_ids")
        )
        if source_pattern and isinstance(source_pattern, list):
            source_pattern = ", ".join(str(x) for x in source_pattern)

    return RoutingRuleSimpleResponse(
        id=rule.id,
        name=rule.name,
        priority=rule.priority,
        source_pattern=source_pattern,
        target_system_ids=target_system_ids,
        is_active=rule.is_active,
        is_published=rule.is_published,
        match_count=rule.match_count if rule.match_count else 0,
        last_match_at=rule.last_match_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _model_to_full_response(rule: RoutingRule) -> dict:
    """将RoutingRule模型转换为完整响应字典"""
    target_systems = rule.target_systems if rule.target_systems else []

    # 兼容旧版字段与缺省情况，提取目标系统ID列表
    target_system_ids: List[str] = []
    if rule.target_system_ids:
        target_system_ids = [str(tid) for tid in rule.target_system_ids]
    elif target_systems:
        for ts in target_systems:
            if isinstance(ts, dict) and ts.get("id"):
                target_system_ids.append(str(ts["id"]))

    response = {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "priority": rule.priority,
        "source_config": rule.source_config if rule.source_config else {},
        "pipeline": rule.pipeline if rule.pipeline else {},
        "target_systems": target_systems,
        "target_system_ids": target_system_ids,
        "is_active": rule.is_active,
        "is_published": rule.is_published,
        "match_count": rule.match_count if rule.match_count else 0,
        "last_match_at": rule.last_match_at.isoformat() if rule.last_match_at else None,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }

    # 兼容旧版API字段
    if rule.conditions:
        response["conditions"] = rule.conditions
    if rule.logical_operator:
        response["logical_operator"] = rule.logical_operator

    return response


@router.get("/simple")
async def list_routing_rules_simple(
    page: int = 1,
    limit: int = 20,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则简化列表（用于前端列表展示）"""
    repo = RoutingRuleRepository(db)

    # 参数验证
    if page < 1:
        return error_response(
            error="Invalid page number",
            detail="页码必须大于等于1",
            code=400
        )
    if limit < 1 or limit > 100:
        return error_response(
            error="Invalid limit",
            detail="每页数量必须在1-100之间",
            code=400
        )

    # 计算偏移量
    skip = (page - 1) * limit

    # 构建过滤条件
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_published is not None:
        filters["is_published"] = is_published

    # 获取数据
    rules = await repo.get_all(skip=skip, limit=limit, **filters)
    total = await repo.count(**filters)

    # 转换为简化响应
    items = [_model_to_simple_response(rule).model_dump(mode='json') for rule in rules]

    return paginated_response(
        items=items,
        page=page,
        limit=limit,
        total=total,
        message="获取路由规则列表成功"
    )


@router.get("/")
async def list_routing_rules(
    page: int = 1,
    limit: int = 20,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则完整列表"""
    repo = RoutingRuleRepository(db)

    # 参数验证
    if page < 1:
        return error_response(
            error="Invalid page number",
            detail="页码必须大于等于1",
            code=400
        )
    if limit < 1 or limit > 100:
        return error_response(
            error="Invalid limit",
            detail="每页数量必须在1-100之间",
            code=400
        )

    # 计算偏移量
    skip = (page - 1) * limit

    # 构建过滤条件
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_published is not None:
        filters["is_published"] = is_published

    # 获取数据
    rules = await repo.get_all(skip=skip, limit=limit, **filters)
    total = await repo.count(**filters)

    # 转换为完整响应
    items = [_model_to_full_response(rule) for rule in rules]

    return paginated_response(
        items=items,
        page=page,
        limit=limit,
        total=total,
        message="获取路由规则列表成功"
    )


@router.get("/{id}")
async def get_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则详情"""
    repo = RoutingRuleRepository(db)
    rule = await repo.get(id)

    if not rule:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    return success_response(
        data=_model_to_full_response(rule),
        message="获取路由规则成功"
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_routing_rule(
    data: RoutingRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建路由规则"""
    repo = RoutingRuleRepository(db)

    try:
        # 准备source_config数据，确保UUID转换为字符串
        source_config_data = data.source_config.model_dump()
        if 'source_ids' in source_config_data and source_config_data['source_ids']:
            source_config_data['source_ids'] = [str(sid) for sid in source_config_data['source_ids']]

        # 准备pipeline数据
        pipeline_data = data.pipeline.model_dump()

        # 准备target_systems数据，将UUID转换为字符串
        target_systems_data = []
        for ts in data.target_systems:
            ts_dict = ts.model_dump()
            # 确保id是字符串而不是UUID对象
            if 'id' in ts_dict and ts_dict['id'] is not None:
                ts_dict['id'] = str(ts_dict['id'])
            target_systems_data.append(ts_dict)

        # 准备兼容旧版字段
        conditions_data = None
        if data.conditions:
            conditions_data = [cond.model_dump() for cond in data.conditions]

        target_system_ids = None
        if data.conditions:  # 如果使用旧版API，从target_systems提取ID
            target_system_ids = [str(ts.id) for ts in data.target_systems]

        rule = await repo.create(
            name=data.name,
            description=data.description,
            priority=data.priority,
            source_config=source_config_data,
            pipeline=pipeline_data,
            target_systems=target_systems_data,
            conditions=conditions_data,
            logical_operator=data.logical_operator if data.logical_operator else None,
            target_system_ids=target_system_ids,
            data_transformation=None,
            is_active=True,
            is_published=data.is_published,
        )

        await db.commit()

        # 注册到网关
        gateway_manager = get_gateway_manager()
        try:
            rule_schema = RoutingRuleResponse(**_model_to_full_response(rule))
            await gateway_manager.register_routing_rule(rule_schema)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("注册路由规则到网关失败: %s", exc, exc_info=True)

        return success_response(
            data=_model_to_full_response(rule),
            message="路由规则创建成功",
            code=201
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"创建路由规则失败: {e}")
        logger.exception(e)
        return error_response(
            error="创建失败",
            detail=str(e),
            code=500
        )


@router.put("/{id}")
async def update_routing_rule(
    id: UUID,
    data: RoutingRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新路由规则"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    # 构建更新数据
    update_data = {}

    # 处理基本字段
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.priority is not None:
        update_data["priority"] = data.priority

    # 处理source_config
    if data.source_config is not None:
        update_data["source_config"] = data.source_config.model_dump()

    # 处理pipeline
    if data.pipeline is not None:
        update_data["pipeline"] = data.pipeline.model_dump()

    # 处理target_systems
    if data.target_systems is not None:
        update_data["target_systems"] = [ts.model_dump() for ts in data.target_systems]
        # 同时更新target_system_ids以保持兼容
        update_data["target_system_ids"] = [str(ts.id) for ts in data.target_systems]

    # 处理兼容旧版字段
    if data.conditions is not None:
        update_data["conditions"] = [cond.model_dump() for cond in data.conditions]
    if data.logical_operator is not None:
        update_data["logical_operator"] = data.logical_operator

    # 处理状态字段
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    if data.is_published is not None:
        update_data["is_published"] = data.is_published

    updated = await repo.update(id, **update_data)
    await db.commit()

    gateway_manager = get_gateway_manager()
    try:
        rule_schema = RoutingRuleResponse(**_model_to_full_response(updated))
        await gateway_manager.reload_routing_rule(rule_schema)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("刷新路由规则失败: %s", exc, exc_info=True)

    return success_response(
        data=_model_to_full_response(updated),
        message="路由规则更新成功"
    )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除路由规则"""
    repo = RoutingRuleRepository(db)

    success = await repo.delete(id)
    if not success:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    await db.commit()

    return success_response(
        data=None,
        message="路由规则删除成功"
    )


@router.post("/{id}/publish")
async def publish_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """发布路由规则"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    success = await repo.publish(id)
    if not success:
        return error_response(
            error="Publish Failed",
            detail="发布路由规则失败",
            code=500
        )

    await db.commit()

    updated_rule = await repo.get(id)
    if updated_rule:
        gateway_manager = get_gateway_manager()
        try:
            rule_schema = RoutingRuleResponse(**_model_to_full_response(updated_rule))
            await gateway_manager.register_routing_rule(rule_schema)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("发布后注册路由规则失败: %s", exc, exc_info=True)

    return success_response(
        data=_model_to_full_response(updated_rule) if updated_rule else None,
        message="路由规则发布成功"
    )


@router.post("/{id}/unpublish")
async def unpublish_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取消发布路由规则"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    success = await repo.unpublish(id)
    if not success:
        return error_response(
            error="Unpublish Failed",
            detail="取消发布路由规则失败",
            code=500
        )

    await db.commit()

    gateway_manager = get_gateway_manager()
    await gateway_manager.unregister_routing_rule(id)

    updated_rule = await repo.get(id)
    return success_response(
        data=_model_to_full_response(updated_rule) if updated_rule else None,
        message="路由规则取消发布成功"
    )


@router.post("/{id}/reload")
async def reload_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """重新加载路由规则到网关"""
    repo = RoutingRuleRepository(db)

    rule = await repo.get(id)
    if not rule:
        return error_response(
            error="Not Found",
            detail=f"路由规则 {id} 不存在",
            code=404
        )

    gateway_manager = get_gateway_manager()

    try:
        rule_schema = RoutingRuleResponse(**_model_to_full_response(rule))
        await gateway_manager.reload_routing_rule(rule_schema)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("重新加载路由规则失败: %s", exc, exc_info=True)
        return error_response(
            error="Reload Failed",
            detail=str(exc),
            code=500
        )

    return success_response(
        data={
            "id": str(rule_schema.id),
            "status": "reloaded"
        },
        message="路由规则重新加载成功"
    )


__all__ = ["router"]
