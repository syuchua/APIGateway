"""
目标系统管理API
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.target_system import TargetSystemRepository
from app.schemas.target_system import (
    TargetSystemCreate,
    TargetSystemUpdate,
    TargetSystemResponse,
)
from app.models.target_system import TargetSystem
from app.core.gateway.manager import get_gateway_manager

router = APIRouter()


def _ts_to_response(ts: TargetSystem) -> dict:
    """将TargetSystem模型转换为响应字典"""
    forwarder_config = ts.forwarder_config or {}
    auth_config = forwarder_config.get("auth_config") if isinstance(forwarder_config, dict) else None

    return {
        "id": ts.id,
        "name": ts.name,
        "description": ts.description,
        "protocol_type": ts.protocol_type,
        "is_active": ts.is_active,
        "target_address": forwarder_config.get("target_address"),
        "target_port": forwarder_config.get("target_port"),
        "endpoint_path": forwarder_config.get("endpoint_path", "/"),
        "timeout": forwarder_config.get("timeout", 30),
        "retry_count": forwarder_config.get("retry_count", 3),
        "batch_size": forwarder_config.get("batch_size", 1),
        "transform_config": ts.transform_config,
        "forwarder_config": forwarder_config,
        "auth_config": auth_config,
        "created_at": ts.created_at,
        "updated_at": ts.updated_at,
    }


@router.post("/", response_model=TargetSystemResponse, status_code=status.HTTP_201_CREATED)
async def create_target_system(
    data: TargetSystemCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建目标系统"""
    repo = TargetSystemRepository(db)

    # 构建endpoint（包含路径）
    endpoint = f"{data.protocol_type.lower()}://{data.target_address}:{data.target_port}{data.endpoint_path}"

    # 构建forwarder_config
    forwarder_config = {
        "target_address": data.target_address,
        "target_port": data.target_port,
        "endpoint_path": data.endpoint_path,
        "timeout": data.timeout,
        "retry_count": data.retry_count,
        "batch_size": data.batch_size,
    }

    ts = await repo.create(
        name=data.name,
        description=data.description,
        protocol_type=data.protocol_type,  # 已经是字符串值了
        endpoint=endpoint,
        is_active=True,
        forwarder_config=forwarder_config,
        transform_config=data.transform_config,
    )

    await db.commit()
    return TargetSystemResponse(**_ts_to_response(ts))


@router.get("/", response_model=List[TargetSystemResponse])
async def list_target_systems(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """获取目标系统列表"""
    repo = TargetSystemRepository(db)

    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active

    systems = await repo.get_all(skip=skip, limit=limit, **filters)
    return [TargetSystemResponse(**_ts_to_response(ts)) for ts in systems]


@router.get("/{id}", response_model=TargetSystemResponse)
async def get_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取目标系统详情"""
    repo = TargetSystemRepository(db)
    ts = await repo.get(id)

    if not ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    return TargetSystemResponse(**_ts_to_response(ts))


@router.put("/{id}", response_model=TargetSystemResponse)
async def update_target_system(
    id: UUID,
    data: TargetSystemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新目标系统"""
    repo = TargetSystemRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    # 构建更新数据
    update_data = data.model_dump(exclude_unset=True)

    # 处理forwarder_config
    if any(k in update_data for k in ["target_address", "target_port", "endpoint_path", "timeout", "retry_count", "batch_size"]):
        forwarder_config = existing.forwarder_config.copy() if existing.forwarder_config else {}

        if "target_address" in update_data:
            forwarder_config["target_address"] = update_data.pop("target_address")
        if "target_port" in update_data:
            forwarder_config["target_port"] = update_data.pop("target_port")
        if "endpoint_path" in update_data:
            forwarder_config["endpoint_path"] = update_data.pop("endpoint_path")
        if "timeout" in update_data:
            forwarder_config["timeout"] = update_data.pop("timeout")
        if "retry_count" in update_data:
            forwarder_config["retry_count"] = update_data.pop("retry_count")
        if "batch_size" in update_data:
            forwarder_config["batch_size"] = update_data.pop("batch_size")

        update_data["forwarder_config"] = forwarder_config

        # 更新endpoint
        target_addr = forwarder_config.get("target_address", existing.forwarder_config.get("target_address"))
        target_port = forwarder_config.get("target_port", existing.forwarder_config.get("target_port"))
        endpoint_path = forwarder_config.get("endpoint_path", existing.forwarder_config.get("endpoint_path", "/"))
        protocol = update_data.get("protocol_type", existing.protocol_type)
        update_data["endpoint"] = f"{protocol.lower()}://{target_addr}:{target_port}{endpoint_path}"

    updated = await repo.update(id, **update_data)
    await db.commit()

    return TargetSystemResponse(**_ts_to_response(updated))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除目标系统"""
    repo = TargetSystemRepository(db)

    success = await repo.delete(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    await db.commit()


@router.post("/{id}/start")
async def start_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启动目标系统（注册到转发器）"""
    repo = TargetSystemRepository(db)

    # 检查目标系统是否存在
    ts = await repo.get(id)
    if not ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    # 检查是否已经激活
    if not ts.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"目标系统 {id} 未激活，请先激活目标系统"
        )

    # 获取网关管理器并注册目标系统
    gateway_manager = get_gateway_manager()

    try:
        # 将目标系统注册到ForwarderManager
        target_response = TargetSystemResponse(**_ts_to_response(ts))
        await gateway_manager.register_target_system(target_response)

        return {
            "message": f"目标系统 {ts.name} 注册成功",
            "id": str(id),
            "status": "registered"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册目标系统失败: {str(e)}"
        )


@router.post("/{id}/stop")
async def stop_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """停止目标系统（从转发器注销）"""
    repo = TargetSystemRepository(db)

    # 检查目标系统是否存在
    ts = await repo.get(id)
    if not ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    # 获取网关管理器并注销目标系统
    gateway_manager = get_gateway_manager()

    try:
        await gateway_manager.unregister_target_system(id)

        return {
            "message": f"目标系统 {ts.name} 已注销",
            "id": str(id),
            "status": "unregistered"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注销目标系统失败: {str(e)}"
        )


@router.get("/{id}/status")
async def get_target_system_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取目标系统运行状态"""
    repo = TargetSystemRepository(db)

    # 检查目标系统是否存在
    ts = await repo.get(id)
    if not ts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标系统 {id} 不存在"
        )

    # 获取网关管理器状态
    gateway_manager = get_gateway_manager()

    # 检查目标系统是否已注册到ForwarderManager
    forwarder_stats = gateway_manager.data_pipeline.forwarder_manager.get_stats()
    target_id_str = str(id)
    is_registered = target_id_str in forwarder_stats.get("targets", {})

    return {
        "id": str(id),
        "name": ts.name,
        "protocol_type": ts.protocol_type,
        "is_active": ts.is_active,
        "is_registered": is_registered,
        "endpoint": ts.endpoint,
        "total_messages": ts.total_forwarded,
        "failed_messages": ts.total_failed,
        "last_message_at": ts.last_forward_at.isoformat() if ts.last_forward_at else None,
    }


__all__ = ["router"]
