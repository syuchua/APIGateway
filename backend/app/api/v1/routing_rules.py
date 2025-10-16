"""
路由规则管理API
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.routing_rule import RoutingRuleRepository
from app.schemas.routing_rule import (
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
)
from app.models.routing_rule import RoutingRule

router = APIRouter()


def _rule_to_response(rule: RoutingRule) -> dict:
    """将RoutingRule模型转换为响应字典（业务导向）"""
    response = {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "priority": rule.priority,
        "source_config": rule.source_config if rule.source_config else {},
        "pipeline": rule.pipeline if rule.pipeline else {},
        "target_systems": rule.target_systems if rule.target_systems else [],
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


@router.post("/", response_model=RoutingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_rule(
    data: RoutingRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建路由规则（业务导向）"""
    repo = RoutingRuleRepository(db)

    # 准备source_config数据
    source_config_data = data.source_config.model_dump()

    # 准备pipeline数据
    pipeline_data = data.pipeline.model_dump()

    # 准备target_systems数据
    target_systems_data = [ts.model_dump() for ts in data.target_systems]

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
    return RoutingRuleResponse(**_rule_to_response(rule))


@router.get("/", response_model=List[RoutingRuleResponse])
async def list_routing_rules(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则列表"""
    repo = RoutingRuleRepository(db)

    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_published is not None:
        filters["is_published"] = is_published

    rules = await repo.get_all(skip=skip, limit=limit, **filters)
    return [RoutingRuleResponse(**_rule_to_response(rule)) for rule in rules]


@router.get("/{id}", response_model=RoutingRuleResponse)
async def get_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取路由规则详情"""
    repo = RoutingRuleRepository(db)
    rule = await repo.get(id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路由规则 {id} 不存在"
        )

    return RoutingRuleResponse(**_rule_to_response(rule))


@router.put("/{id}", response_model=RoutingRuleResponse)
async def update_routing_rule(
    id: UUID,
    data: RoutingRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新路由规则（业务导向）"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路由规则 {id} 不存在"
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

    return RoutingRuleResponse(**_rule_to_response(updated))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除路由规则"""
    repo = RoutingRuleRepository(db)

    success = await repo.delete(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路由规则 {id} 不存在"
        )

    await db.commit()


@router.post("/{id}/publish", response_model=RoutingRuleResponse)
async def publish_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """发布路由规则"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路由规则 {id} 不存在"
        )

    success = await repo.publish(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发布路由规则失败"
        )

    await db.commit()

    # 重新获取更新后的规则
    updated_rule = await repo.get(id)
    return RoutingRuleResponse(**_rule_to_response(updated_rule))


@router.post("/{id}/unpublish", response_model=RoutingRuleResponse)
async def unpublish_routing_rule(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取消发布路由规则"""
    repo = RoutingRuleRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路由规则 {id} 不存在"
        )

    success = await repo.unpublish(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消发布路由规则失败"
        )

    await db.commit()

    # 重新获取更新后的规则
    updated_rule = await repo.get(id)
    return RoutingRuleResponse(**_rule_to_response(updated_rule))


__all__ = ["router"]
