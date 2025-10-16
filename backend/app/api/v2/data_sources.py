"""
数据源管理API v2 (使用新的嵌套Schema和ApiResponse)
"""
import json
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gateway.manager import get_gateway_manager
from app.db.database import get_db
from app.models.data_source import DataSource
from app.repositories.data_source import DataSourceRepository
from app.schemas.common import ProtocolType
from app.schemas.data_source_v2 import (
    ConnectionConfig,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ParseConfig,
)
from app.schemas.response import error_response, paginated_response, success_response

router = APIRouter()


def _build_connection_config(ds: DataSource) -> ConnectionConfig:
    """根据数据库模型构建ConnectionConfig，保留自定义字段"""
    raw_config: Dict[str, Any] = ds.connection_config or {}

    listen_address = (
        raw_config.get("listen_address")
        or raw_config.get("host")
        or raw_config.get("broker_host")
        or "0.0.0.0"
    )
    listen_port = (
        raw_config.get("listen_port")
        or raw_config.get("port")
        or raw_config.get("broker_port")
        or 1
    )

    connection_config = ConnectionConfig(
        listen_address=listen_address,
        listen_port=int(listen_port),
        max_connections=raw_config.get("max_connections", 100),
        timeout_seconds=raw_config.get("timeout_seconds", 30),
        buffer_size=raw_config.get("buffer_size", 8192),
    )

    # 附加自定义字段（extra="allow"）
    for key, value in raw_config.items():
        if key not in {"listen_address", "listen_port", "max_connections", "timeout_seconds", "buffer_size"}:
            setattr(connection_config, key, value)

    return connection_config


def _build_parse_config(ds: DataSource) -> ParseConfig:
    """根据数据库模型构建ParseConfig"""
    raw_config: Dict[str, Any] = ds.connection_config or {}
    return ParseConfig(
        auto_parse=raw_config.get("auto_parse", True),
        frame_schema_id=ds.frame_schema_id,
        parse_options=raw_config.get("parse_options"),
    )


def _model_to_response(ds: DataSource) -> DataSourceResponse:
    """将ORM模型转换为响应Schema"""
    connection_config = _build_connection_config(ds)
    parse_config = _build_parse_config(ds)

    protocol_type_upper = ds.protocol_type.upper()

    return DataSourceResponse(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        protocol_type=ProtocolType(protocol_type_upper),
        connection_config=connection_config,
        parse_config=parse_config,
        is_active=ds.is_active,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


def _prepare_adapter_config(ds: DataSource, protocol: ProtocolType) -> Dict[str, Any]:
    """根据数据源协议构建适配器配置"""
    conn: Dict[str, Any] = ds.connection_config or {}
    config: Dict[str, Any] = {
        "name": ds.name,
        "is_active": ds.is_active,
        "data_source_id": str(ds.id),
    }

    auto_parse = conn.get("auto_parse", True)

    if protocol == ProtocolType.UDP:
        listen_port = conn.get("listen_port")
        if listen_port is None:
            raise ValueError("UDP数据源缺少listen_port配置")

        config.update(
            {
                "listen_address": conn.get("listen_address", "0.0.0.0"),
                "listen_port": int(listen_port),
                "buffer_size": conn.get("buffer_size", 8192),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": auto_parse,
            }
        )

    elif protocol == ProtocolType.TCP:
        listen_port = conn.get("listen_port")
        if listen_port is None:
            raise ValueError("TCP数据源缺少listen_port配置")

        config.update(
            {
                "listen_address": conn.get("listen_address", "0.0.0.0"),
                "listen_port": int(listen_port),
                "buffer_size": conn.get("buffer_size", 8192),
                "max_connections": conn.get("max_connections", 100),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": auto_parse,
            }
        )

    elif protocol == ProtocolType.HTTP:
        endpoint = conn.get("endpoint") or conn.get("url") or "/"
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint.lstrip('/')}"

        config.update(
            {
                "endpoint": endpoint,
                "method": (conn.get("method") or "POST").upper(),
                "frame_schema_id": ds.frame_schema_id,
                "auto_parse": auto_parse,
            }
        )

    elif protocol == ProtocolType.WEBSOCKET:
        endpoint = conn.get("endpoint") or conn.get("url") or "/ws"
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint.lstrip('/')}"

        config.update(
            {
                "endpoint": endpoint,
                "max_connections": conn.get("max_connections", 100),
            }
        )

    elif protocol == ProtocolType.MQTT:
        broker_host = (
            conn.get("broker_host")
            or conn.get("host")
            or conn.get("listen_address")
        )
        broker_port = (
            conn.get("broker_port")
            or conn.get("port")
            or conn.get("listen_port")
        )
        topics_raw = conn.get("topics") or conn.get("mqtt_topics")

        if isinstance(topics_raw, str):
            topics = [topic.strip() for topic in topics_raw.split(",") if topic.strip()]
        elif isinstance(topics_raw, list):
            topics = topics_raw
        else:
            topics = []

        if not broker_host or broker_port is None:
            raise ValueError("MQTT数据源缺少broker_host或broker_port配置")
        if not topics:
            raise ValueError("MQTT数据源缺少订阅主题配置")

        config.update(
            {
                "broker_host": broker_host,
                "broker_port": int(broker_port),
                "topics": topics,
                "client_id": conn.get("client_id"),
                "username": conn.get("username") or conn.get("mqtt_username"),
                "password": conn.get("password") or conn.get("mqtt_password"),
                "qos": conn.get("qos", conn.get("mqtt_qos", 0)),
            }
        )

    else:
        raise ValueError(f"协议类型 {ds.protocol_type} 暂未实现")

    return config


@router.post("/{id}/ingest")
async def ingest_http_data(
    id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """向HTTP数据源注入测试数据（用于联调脚本）。"""

    repo = DataSourceRepository(db)
    ds = await repo.get(id)

    if not ds:
        return error_response(
            error="数据源不存在",
            detail=f"ID为 {id} 的数据源不存在",
            code=404
        )

    if ds.protocol_type.lower() != "http":
        return error_response(
            error="协议不匹配",
            detail="仅支持向 HTTP 数据源注入测试数据",
            code=400
        )

    gateway_manager = get_gateway_manager()

    if not gateway_manager.is_running:
        await gateway_manager.start()

    adapter = gateway_manager.adapters.get(str(id))
    if adapter is None:
        return error_response(
            error="适配器未启动",
            detail="请先通过 /start 接口启动该数据源",
            code=400
        )

    if not adapter.is_running:  # type: ignore[attr-defined]
        await adapter.start()  # type: ignore[attr-defined]

    try:
        raw_body = await request.body()
        payload: Any
        if raw_body:
            try:
                payload = json.loads(raw_body.decode())
            except json.JSONDecodeError:
                payload = raw_body
        else:
            payload = {}

        client_host = request.client.host if request.client else "unknown"
        headers = {key: value for key, value in request.headers.items()}

        await adapter.receive_data(  # type: ignore[attr-defined]
            data=payload,
            source_address=client_host,
            headers=headers
        )

        return success_response(
            data={"status": "ingested", "source_id": str(id)},
            message="数据已注入"
        )

    except Exception as exc:  # pylint: disable=broad-except
        return error_response(
            error="数据注入失败",
            detail=str(exc),
            code=500
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建数据源

    返回格式: ApiResponse包装
    """
    repo = DataSourceRepository(db)

    connection_config = data.connection_config.model_dump(mode="json", exclude_none=True)
    if data.parse_config:
        connection_config["auto_parse"] = data.parse_config.auto_parse
        if data.parse_config.parse_options is not None:
            connection_config["parse_options"] = data.parse_config.parse_options
    else:
        connection_config["auto_parse"] = True

    try:
        protocol_value = (
            data.protocol_type.value if hasattr(data.protocol_type, "value") else data.protocol_type
        )
        protocol_value = protocol_value.lower()

        ds: DataSource = await repo.create(
            name=data.name,
            description=data.description,
            protocol_type=protocol_value,
            is_active=True,
            connection_config=connection_config,
            frame_schema_id=data.parse_config.frame_schema_id if data.parse_config else None,
        )

        await db.commit()
        await db.refresh(ds)

        response = _model_to_response(ds)

        return success_response(
            data=response.model_dump(mode="json"),
            message="数据源创建成功",
            code=201,
        )

    except Exception as exc:  # pylint: disable=broad-except
        await db.rollback()
        return error_response(
            error="创建数据源失败",
            detail=str(exc),
            code=500,
        )


@router.get("/")
async def list_data_sources(
    page: int = 1,
    limit: int = 20,
    protocol: Optional[ProtocolType] = None,
    protocol_type: Optional[ProtocolType] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    获取数据源列表

    返回格式: PaginatedResponse
    """
    repo = DataSourceRepository(db)

    if page < 1:
        return error_response(
            error="Invalid page number",
            detail="页码必须大于等于1",
            code=400,
        )
    if limit < 1 or limit > 100:
        return error_response(
            error="Invalid limit",
            detail="每页数量必须在1-100之间",
            code=400,
        )

    skip = (page - 1) * limit

    filters: Dict[str, Any] = {}
    protocol_filter = protocol or protocol_type
    if protocol_filter:
        filters["protocol_type"] = protocol_filter.value
    if is_active is not None:
        filters["is_active"] = is_active

    try:
        sources = await repo.get_all(skip=skip, limit=limit, **filters)
        total = await repo.count(**filters)
        response_list = [_model_to_response(ds).model_dump(mode="json") for ds in sources]

        return paginated_response(
            items=response_list,
            page=page,
            limit=limit,
            total=total,
            message="获取数据源列表成功",
        )

    except Exception as exc:  # pylint: disable=broad-except
        return error_response(
            error="获取数据源列表失败",
            detail=str(exc),
            code=500,
        )


@router.get("/{id}")
async def get_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    获取数据源详情

    返回格式: ApiResponse包装
    """
    repo = DataSourceRepository(db)

    try:
        ds = await repo.get(id)

        if not ds:
            return error_response(
                error="数据源不存在",
                detail=f"ID为 {id} 的数据源不存在",
                code=404,
            )

        response = _model_to_response(ds)

        return success_response(
            data=response.model_dump(mode="json"),
            message="获取数据源详情成功",
        )

    except Exception as exc:  # pylint: disable=broad-except
        return error_response(
            error="获取数据源详情失败",
            detail=str(exc),
            code=500,
        )


@router.put("/{id}")
async def update_data_source(
    id: UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新数据源

    返回格式: ApiResponse包装
    """
    repo = DataSourceRepository(db)

    try:
        existing = await repo.get(id)
        if not existing:
            return error_response(
                error="数据源不存在",
                detail=f"ID为 {id} 的数据源不存在",
                code=404,
            )

        update_dict: Dict[str, Any] = {}

        if data.name is not None:
            update_dict["name"] = data.name
        if data.description is not None:
            update_dict["description"] = data.description
        if data.is_active is not None:
            update_dict["is_active"] = data.is_active

        if data.connection_config or data.parse_config:
            connection_config: Dict[str, Any] = (
                existing.connection_config.copy() if existing.connection_config else {}
            )

            if data.connection_config:
                connection_updates = data.connection_config.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude_none=True,
                )
                connection_config.update(connection_updates)

            if data.parse_config:
                fields_set = getattr(data.parse_config, "model_fields_set", set())

                if "auto_parse" in fields_set:
                    connection_config["auto_parse"] = data.parse_config.auto_parse

                if "parse_options" in fields_set:
                    if data.parse_config.parse_options is None:
                        connection_config.pop("parse_options", None)
                    else:
                        connection_config["parse_options"] = data.parse_config.parse_options

                if "frame_schema_id" in fields_set:
                    update_dict["frame_schema_id"] = data.parse_config.frame_schema_id

            update_dict["connection_config"] = connection_config

        updated = await repo.update(id, **update_dict)
        await db.commit()
        await db.refresh(updated)

        response = _model_to_response(updated)

        return success_response(
            data=response.model_dump(mode="json"),
            message="数据源更新成功",
        )

    except Exception as exc:  # pylint: disable=broad-except
        await db.rollback()
        return error_response(
            error="更新数据源失败",
            detail=str(exc),
            code=500,
        )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    删除数据源

    返回格式: ApiResponse包装
    """
    repo = DataSourceRepository(db)

    try:
        success = await repo.delete(id)
        if not success:
            return error_response(
                error="数据源不存在",
                detail=f"ID为 {id} 的数据源不存在",
                code=404,
            )

        await db.commit()

        return success_response(
            data={"id": str(id)},
            message="数据源删除成功",
        )

    except Exception as exc:  # pylint: disable=broad-except
        await db.rollback()
        return error_response(
            error="删除数据源失败",
            detail=str(exc),
            code=500,
        )


@router.post("/{id}/start")
async def start_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启动数据源"""
    repo = DataSourceRepository(db)
    ds = await repo.get(id)

    if not ds:
        return error_response(
            error="数据源不存在",
            detail=f"ID为 {id} 的数据源不存在",
            code=404,
        )

    if not ds.is_active:
        return error_response(
            error="数据源未激活",
            detail=f"数据源 {id} 未激活，请先启用数据源",
            code=400,
        )

    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    if adapter_id in gateway_manager.adapters:
        return error_response(
            error="数据源已运行",
            detail=f"数据源 {id} 已经在运行中",
            code=400,
        )

    try:
        protocol = ProtocolType(ds.protocol_type.upper())
        adapter_config = _prepare_adapter_config(ds, protocol)

        await gateway_manager.add_adapter(
            adapter_id=adapter_id,
            protocol=protocol,
            config=adapter_config,
            frame_schema=None,
        )

        return success_response(
            data={"id": str(id), "status": "running"},
            message=f"数据源 {ds.name} 启动成功",
        )

    except ValueError as exc:
        return error_response(
            error="配置错误",
            detail=str(exc),
            code=400,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return error_response(
            error="启动数据源失败",
            detail=str(exc),
            code=500,
        )


@router.post("/{id}/stop")
async def stop_data_source(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """停止数据源"""
    repo = DataSourceRepository(db)
    ds = await repo.get(id)

    if not ds:
        return error_response(
            error="数据源不存在",
            detail=f"ID为 {id} 的数据源不存在",
            code=404,
        )

    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    if adapter_id not in gateway_manager.adapters:
        return error_response(
            error="数据源未运行",
            detail=f"数据源 {id} 当前未运行",
            code=400,
        )

    try:
        await gateway_manager.remove_adapter(adapter_id)
        return success_response(
            data={"id": str(id), "status": "stopped"},
            message=f"数据源 {ds.name} 已停止",
        )
    except Exception as exc:  # pylint: disable=broad-except
        return error_response(
            error="停止数据源失败",
            detail=str(exc),
            code=500,
        )


@router.get("/{id}/status")
async def get_data_source_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取数据源运行状态"""
    repo = DataSourceRepository(db)
    ds = await repo.get(id)

    if not ds:
        return error_response(
            error="数据源不存在",
            detail=f"ID为 {id} 的数据源不存在",
            code=404,
        )

    gateway_manager = get_gateway_manager()
    adapter_id = str(id)

    is_running = adapter_id in gateway_manager.adapters
    adapter_stats = gateway_manager.get_adapter_stats(adapter_id) if is_running else None

    return success_response(
        data={
            "id": str(id),
            "name": ds.name,
            "protocol_type": ds.protocol_type.upper(),
            "is_active": ds.is_active,
            "is_running": is_running,
            "stats": adapter_stats,
            "total_messages": ds.total_messages,
            "last_message_at": ds.last_message_at.isoformat() if ds.last_message_at else None,
        },
        message="获取状态成功",
    )


__all__ = ["router"]
