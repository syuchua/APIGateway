"""
数据源管理API
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.data_source import DataSourceRepository
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
)
from app.schemas.common import ProtocolType
from app.models.data_source import DataSource
from app.core.gateway.manager import get_gateway_manager

router = APIRouter()


def _ds_to_response(ds: DataSource) -> dict:
    """将DataSource模型转换为响应字典"""
    return {
        "id": ds.id,
        "name": ds.name,
        "description": ds.description,
        "protocol_type": ds.protocol_type,
        "is_active": ds.is_active,
        "frame_schema_id": ds.frame_schema_id,
        "listen_address": ds.connection_config.get("listen_address"),
        "listen_port": ds.connection_config.get("listen_port"),
        "auto_parse": ds.connection_config.get("auto_parse", True),
        "max_connections": ds.connection_config.get("max_connections"),
        "timeout_seconds": ds.connection_config.get("timeout_seconds"),
        "buffer_size": ds.connection_config.get("buffer_size"),
        "created_at": ds.created_at,
        "updated_at": ds.updated_at,
    }


@router.post("/", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建数据源"""
    repo = DataSourceRepository(db)

    # 构建connection_config
    connection_config = {
        "listen_address": data.listen_address,
        "listen_port": data.listen_port,
        "auto_parse": data.auto_parse,
        "max_connections": data.max_connections,
        "timeout_seconds": data.timeout_seconds,
        "buffer_size": data.buffer_size,
    }

    ds = await repo.create(
        name=data.name,
        description=data.description,
        protocol_type=data.protocol_type,  # 已经是字符串值了
        is_active=True,
        connection_config=connection_config,
        frame_schema_id=data.frame_schema_id,
    )

    await db.commit()
    return DataSourceResponse(**_ds_to_response(ds))


@router.get("/", response_model=List[DataSourceResponse])
async def list_data_sources(
    skip: int = 0,
    limit: int = 100,
    protocol: ProtocolType = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """获取数据源列表"""
    repo = DataSourceRepository(db)

    filters = {}
    if protocol:
        filters["protocol_type"] = protocol  # 已经是字符串值了
    if is_active is not None:
        filters["is_active"] = is_active

    sources = await repo.get_all(skip=skip, limit=limit, **filters)
    return [DataSourceResponse(**_ds_to_response(ds)) for ds in sources]


@router.get("/{id}", response_model=DataSourceResponse)
async def get_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取数据源详情"""
    repo = DataSourceRepository(db)
    ds = await repo.get(id)

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    return DataSourceResponse(**_ds_to_response(ds))


@router.put("/{id}", response_model=DataSourceResponse)
async def update_data_source(
    id: UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新数据源"""
    repo = DataSourceRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    # 构建更新数据
    update_data = data.model_dump(exclude_unset=True)

    # 处理connection_config
    if any(k in update_data for k in ["listen_address", "listen_port", "max_connections", "timeout_seconds", "buffer_size"]):
        connection_config = existing.connection_config.copy() if existing.connection_config else {}
        if "listen_address" in update_data:
            connection_config["listen_address"] = update_data.pop("listen_address")
        if "listen_port" in update_data:
            connection_config["listen_port"] = update_data.pop("listen_port")
        if "max_connections" in update_data:
            connection_config["max_connections"] = update_data.pop("max_connections")
        if "timeout_seconds" in update_data:
            connection_config["timeout_seconds"] = update_data.pop("timeout_seconds")
        if "buffer_size" in update_data:
            connection_config["buffer_size"] = update_data.pop("buffer_size")
        update_data["connection_config"] = connection_config

    updated = await repo.update(id, **update_data)
    await db.commit()

    return DataSourceResponse(**_ds_to_response(updated))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除数据源"""
    repo = DataSourceRepository(db)

    success = await repo.delete(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    await db.commit()


@router.post("/{id}/start")
async def start_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启动数据源"""
    repo = DataSourceRepository(db)

    # 检查数据源是否存在
    ds = await repo.get(id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    # 检查是否已经激活
    if not ds.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据源 {id} 未激活，请先激活数据源"
        )

    # 获取网关管理器并启动适配器
    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    # 检查适配器是否已存在
    if adapter_id in gateway_manager.adapters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据源 {id} 已经在运行中"
        )

    try:
        # 根据协议类型构建配置字典
        protocol = ProtocolType(ds.protocol_type.upper())

        # 构建适配器配置
        config = {
            "name": ds.name,
            "is_active": ds.is_active,
        }

        # 根据协议类型添加特定配置
        if protocol == ProtocolType.UDP:
            config.update({
                "listen_address": ds.connection_config.get("listen_address", "0.0.0.0"),
                "listen_port": ds.connection_config.get("listen_port"),
                "buffer_size": ds.connection_config.get("buffer_size", 8192),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": ds.connection_config.get("auto_parse", False),
            })
        elif protocol == ProtocolType.TCP:
            config.update({
                "listen_address": ds.connection_config.get("listen_address", "0.0.0.0"),
                "listen_port": ds.connection_config.get("listen_port"),
                "buffer_size": ds.connection_config.get("buffer_size", 8192),
                "max_connections": ds.connection_config.get("max_connections", 100),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": ds.connection_config.get("auto_parse", False),
            })
        elif protocol == ProtocolType.HTTP:
            # HTTP需要endpoint配置
            config.update({
                "endpoint": ds.connection_config.get("endpoint", "/"),
                "method": ds.connection_config.get("method", "POST"),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": ds.connection_config.get("auto_parse", False),
            })
        elif protocol == ProtocolType.WEBSOCKET:
            config.update({
                "endpoint": ds.connection_config.get("endpoint", "/ws"),
                "max_connections": ds.connection_config.get("max_connections", 100),
            })
        elif protocol == ProtocolType.MQTT:
            config.update({
                "broker_host": ds.connection_config.get("broker_host", "localhost"),
                "broker_port": ds.connection_config.get("broker_port", 1883),
                "topics": ds.connection_config.get("topics", []),
                "client_id": ds.connection_config.get("client_id"),
                "username": ds.connection_config.get("username"),
                "password": ds.connection_config.get("password"),
                "qos": ds.connection_config.get("qos", 0),
            })
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"协议类型 {ds.protocol_type} 暂未实现"
            )

        # 使用通用方法添加适配器
        await gateway_manager.add_adapter(
            adapter_id=adapter_id,
            protocol=protocol,
            config=config,
            frame_schema=None  # 可以后续从数据库加载
        )

        return {
            "message": f"数据源 {ds.name} 启动成功",
            "id": str(id),
            "status": "running"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动数据源失败: {str(e)}"
        )


@router.post("/{id}/stop")
async def stop_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """停止数据源"""
    repo = DataSourceRepository(db)

    # 检查数据源是否存在
    ds = await repo.get(id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    # 获取网关管理器并停止适配器
    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    # 检查适配器是否存在
    if adapter_id not in gateway_manager.adapters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据源 {id} 未运行"
        )

    try:
        await gateway_manager.remove_adapter(adapter_id)

        return {
            "message": f"数据源 {ds.name} 已停止",
            "id": str(id),
            "status": "stopped"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止数据源失败: {str(e)}"
        )


@router.get("/{id}/status")
async def get_data_source_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取数据源运行状态"""
    repo = DataSourceRepository(db)

    # 检查数据源是否存在
    ds = await repo.get(id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据源 {id} 不存在"
        )

    # 获取网关管理器状态
    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    is_running = adapter_id in gateway_manager.adapters
    adapter_stats = gateway_manager.get_adapter_stats(adapter_id) if is_running else None

    return {
        "id": str(id),
        "name": ds.name,
        "protocol_type": ds.protocol_type,
        "is_active": ds.is_active,
        "is_running": is_running,
        "stats": adapter_stats,
        "total_messages": ds.total_messages,
        "last_message_at": ds.last_message_at.isoformat() if ds.last_message_at else None,
    }


__all__ = ["router"]
