"""
目标系统管理API v2 (使用新的嵌套Schema和ApiResponse)
"""
from typing import Any, Dict, Optional
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.target_system import TargetSystemRepository
from app.schemas.target_system_v2 import (
    TargetSystemCreate,
    TargetSystemUpdate,
    TargetSystemResponse,
    EndpointConfig,
    AuthConfig,
    ForwarderConfig,
)
from app.schemas.target_system import TargetSystemResponse as LegacyTargetSystemResponse
from app.schemas.response import success_response, error_response, paginated_response
from app.schemas.common import ProtocolType
from app.models.target_system import TargetSystem
from app.core.gateway.manager import get_gateway_manager

router = APIRouter()


def _normalize_encryption_config(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """规范化加密配置，确保布尔与元数据可靠"""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return {"enabled": bool(raw)}

    config = dict(raw)
    enabled = bool(config.get("enabled", False))
    config["enabled"] = enabled

    metadata = config.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("加密配置 metadata 必须是对象")

    if metadata is None and "metadata" in config:
        config.pop("metadata")

    version = config.get("version")
    if version is None and "version" in config:
        config.pop("version")

    return config


def _extract_forwarder_config(ts: TargetSystem) -> Dict[str, Any]:
    """安全地提取并复制forwarder_config"""
    if isinstance(ts.forwarder_config, dict):
        return dict(ts.forwarder_config)
    return {}


def _resolve_endpoint(ts: TargetSystem, forwarder_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据forwarder配置或endpoint字符串解析端点信息
    返回包含目标地址、端口、路径和SSL开关的字典
    """
    target_address = forwarder_cfg.get("target_address")
    target_port = forwarder_cfg.get("target_port")
    endpoint_path = forwarder_cfg.get("endpoint_path") or "/"
    use_ssl = forwarder_cfg.get("use_ssl", False)

    if target_address and target_port:
        return {
            "target_address": target_address,
            "target_port": int(target_port),
            "endpoint_path": endpoint_path or "/",
            "use_ssl": bool(use_ssl),
        }

    # 回退解析 endpoint 字符串
    parsed_address = "localhost"
    parsed_port = 80
    parsed_path = "/"
    parsed_use_ssl = False

    if ts.endpoint:
        try:
            parsed = urlsplit(ts.endpoint)
            parsed_address = parsed.hostname or parsed_address
            if parsed.port:
                parsed_port = parsed.port
            elif parsed.scheme == "https":
                parsed_port = 443
            parsed_path = parsed.path or "/"
            parsed_use_ssl = parsed.scheme == "https"
        except Exception:  # pylint: disable=broad-except
            pass

    return {
        "target_address": parsed_address,
        "target_port": parsed_port,
        "endpoint_path": parsed_path,
        "use_ssl": parsed_use_ssl,
    }


def _build_auth_config(forwarder_cfg: Dict[str, Any]) -> Optional[AuthConfig]:
    """从forwarder配置中提取认证配置"""
    auth_data = forwarder_cfg.get("auth_config")
    if not auth_data:
        return None

    return AuthConfig(
        auth_type=auth_data.get("auth_type", "none"),
        username=auth_data.get("username"),
        password=auth_data.get("password"),
        token=auth_data.get("token"),
        api_key=auth_data.get("api_key"),
        api_key_header=auth_data.get("api_key_header", "X-API-Key"),
        custom_headers=auth_data.get("custom_headers"),
    )


def _build_forwarder_config(forwarder_cfg: Dict[str, Any]) -> ForwarderConfig:
    """构建转发配置"""
    encryption_cfg = None
    raw_encryption = (
        forwarder_cfg.get("encryption")
        or forwarder_cfg.get("encryption_config")
    )
    if raw_encryption is not None:
        try:
            encryption_cfg = _normalize_encryption_config(raw_encryption)
        except ValueError:
            encryption_cfg = None

    return ForwarderConfig(
        timeout=int(forwarder_cfg.get("timeout", 30) or 30),
        retry_count=int(forwarder_cfg.get("retry_count", 3) or 3),
        batch_size=int(forwarder_cfg.get("batch_size", 1) or 1),
        compression=bool(forwarder_cfg.get("compression", False)),
        encryption=encryption_cfg,
    )


def _compute_runtime_status(ts: TargetSystem) -> str:
    """根据GatewayManager状态计算目标系统运行状态"""
    try:
        gateway_manager = get_gateway_manager()
        forwarder_manager = gateway_manager.data_pipeline.forwarder_manager
        target_id = str(ts.id)

        if not ts.is_active:
            return "disconnected"

        has_target = target_id in forwarder_manager.target_systems
        has_forwarder = target_id in forwarder_manager.forwarders

        if has_target and has_forwarder:
            return "connected"
        if has_target and not has_forwarder:
            return "error"
        return "disconnected"
    except Exception:  # pylint: disable=broad-except
        return "error"


def _to_pipeline_response(ts: TargetSystem) -> LegacyTargetSystemResponse:
    """转换为旧版TargetSystemResponse以注册到GatewayManager"""
    forwarder_cfg = _extract_forwarder_config(ts)
    endpoint = _resolve_endpoint(ts, forwarder_cfg)

    # 确保forwarder配置包含基础路由信息，便于转发器使用
    forwarder_cfg.setdefault("target_address", endpoint["target_address"])
    forwarder_cfg.setdefault("target_port", endpoint["target_port"])
    forwarder_cfg.setdefault("endpoint_path", endpoint["endpoint_path"])
    forwarder_cfg.setdefault("use_ssl", endpoint["use_ssl"])
    forwarder_cfg.setdefault("timeout", forwarder_cfg.get("timeout", ts.timeout if hasattr(ts, "timeout") else 30))
    forwarder_cfg.setdefault("retry_count", forwarder_cfg.get("retry_count", ts.retry_count if hasattr(ts, "retry_count") else 3))
    forwarder_cfg.setdefault("batch_size", forwarder_cfg.get("batch_size", ts.batch_size if hasattr(ts, "batch_size") else 1))

    auth_cfg = forwarder_cfg.get("auth_config")
    if auth_cfg is None and hasattr(ts, "auth_config") and ts.auth_config:
        auth_cfg = ts.auth_config.model_dump(mode="json")

    return LegacyTargetSystemResponse(
        id=ts.id,
        name=ts.name,
        description=ts.description,
        protocol_type=ProtocolType(ts.protocol_type.upper()),
        target_address=endpoint["target_address"],
        target_port=endpoint["target_port"],
        endpoint_path=endpoint["endpoint_path"],
        timeout=int(forwarder_cfg.get("timeout", 30) or 30),
        retry_count=int(forwarder_cfg.get("retry_count", 3) or 3),
        batch_size=int(forwarder_cfg.get("batch_size", 1) or 1),
        transform_config=ts.transform_config,
        is_active=ts.is_active,
        created_at=ts.created_at,
        updated_at=ts.updated_at,
        forwarder_config=forwarder_cfg,
        auth_config=auth_cfg,
    )


def _model_to_response(ts: TargetSystem) -> TargetSystemResponse:
    """将ORM模型转换为响应Schema"""
    forwarder_cfg = _extract_forwarder_config(ts)
    endpoint = _resolve_endpoint(ts, forwarder_cfg)

    return TargetSystemResponse(
        id=ts.id,
        name=ts.name,
        description=ts.description,
        protocol_type=ProtocolType(ts.protocol_type.upper()),
        status=_compute_runtime_status(ts),
        endpoint_config=EndpointConfig(**endpoint),
        auth_config=_build_auth_config(forwarder_cfg),
        forwarder_config=_build_forwarder_config(forwarder_cfg),
        transform_rules=ts.transform_config,
        is_active=ts.is_active,
        created_at=ts.created_at,
        updated_at=ts.updated_at,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_target_system(
    data: TargetSystemCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建目标系统

    返回格式: ApiResponse包装
    """
    repo = TargetSystemRepository(db)

    try:
        # 处理协议类型：如果是枚举则获取值，如果是字符串则直接使用
        protocol_value = data.protocol_type.value if hasattr(data.protocol_type, 'value') else data.protocol_type
        # 转换为小写以匹配数据库约束
        protocol_value_lower = protocol_value.lower()

        # 构建endpoint URL
        protocol_prefix = "https" if data.endpoint_config.use_ssl else protocol_value_lower
        endpoint = f"{protocol_prefix}://{data.endpoint_config.target_address}:{data.endpoint_config.target_port}{data.endpoint_config.endpoint_path}"

        # 构建forwarder_config（扁平化存储到数据库，包含auth_config）
        forwarder_config = {
            "target_address": data.endpoint_config.target_address,
            "target_port": data.endpoint_config.target_port,
            "endpoint_path": data.endpoint_config.endpoint_path or "",
            "use_ssl": data.endpoint_config.use_ssl if data.endpoint_config.use_ssl is not None else False,
            "timeout": data.forwarder_config.timeout if data.forwarder_config else 30,
            "retry_count": data.forwarder_config.retry_count if data.forwarder_config else 3,
            "batch_size": data.forwarder_config.batch_size if data.forwarder_config else 1,
            "compression": data.forwarder_config.compression if data.forwarder_config else False,
        }
        if data.forwarder_config and data.forwarder_config.encryption is not None:
            encryption_cfg = _normalize_encryption_config(data.forwarder_config.encryption)
            if encryption_cfg:
                if encryption_cfg.get("enabled"):
                    forwarder_config["encryption"] = encryption_cfg
                else:
                    forwarder_config.pop("encryption", None)

        # 将auth_config合并到forwarder_config中
        if data.auth_config:
            auth_payload = {
                "auth_type": data.auth_config.auth_type,
                "username": data.auth_config.username,
                "password": data.auth_config.password,
                "token": data.auth_config.token,
                "api_key": data.auth_config.api_key,
                "api_key_header": data.auth_config.api_key_header,
                "custom_headers": data.auth_config.custom_headers,
            }
            if data.auth_config.auth_type == "none":
                forwarder_config.pop("auth_config", None)
            else:
                forwarder_config["auth_config"] = auth_payload

        ts = await repo.create(
            name=data.name,
            description=data.description,
            protocol_type=protocol_value_lower,
            endpoint=endpoint,
            is_active=data.is_active,
            forwarder_config=forwarder_config,
            transform_config=data.transform_rules,
        )

        await db.commit()
        await db.refresh(ts)

        response = _model_to_response(ts)

        return success_response(
            data=response.model_dump(mode='json'),
            message="目标系统创建成功",
            code=201
        )

    except Exception as e:
        await db.rollback()
        return error_response(
            error="创建目标系统失败",
            detail=str(e),
            code=500
        )


@router.get("/")
async def list_target_systems(
    page: int = 1,
    limit: int = 20,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """
    获取目标系统列表

    返回格式: PaginatedResponse
    """
    repo = TargetSystemRepository(db)

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

    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active

    try:
        systems = await repo.get_all(skip=skip, limit=limit, **filters)
        total = await repo.count(**filters)
        response_list = [_model_to_response(ts).model_dump(mode='json') for ts in systems]

        return paginated_response(
            items=response_list,
            page=page,
            limit=limit,
            total=total,
            message="获取目标系统列表成功"
        )

    except Exception as e:
        return error_response(
            error="获取目标系统列表失败",
            detail=str(e),
            code=500
        )


@router.get("/{id}")
async def get_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    获取目标系统详情

    返回格式: ApiResponse包装
    """
    repo = TargetSystemRepository(db)

    try:
        ts = await repo.get(id)

        if not ts:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        response = _model_to_response(ts)

        return success_response(
            data=response.model_dump(mode='json'),
            message="获取目标系统详情成功"
        )

    except Exception as e:
        return error_response(
            error="获取目标系统详情失败",
            detail=str(e),
            code=500
        )


@router.put("/{id}")
async def update_target_system(
    id: UUID,
    data: TargetSystemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新目标系统

    返回格式: ApiResponse包装
    """
    repo = TargetSystemRepository(db)

    try:
        # 检查是否存在
        existing = await repo.get(id)
        if not existing:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        # 构建更新数据
        update_dict = {}

        if data.name is not None:
            update_dict["name"] = data.name
        if data.description is not None:
            update_dict["description"] = data.description
        if data.is_active is not None:
            update_dict["is_active"] = data.is_active
        if data.transform_rules is not None:
            update_dict["transform_config"] = data.transform_rules

        forwarder_config = _extract_forwarder_config(existing)
        forwarder_updated = False

        if data.endpoint_config:
            forwarder_config.update({
                "target_address": data.endpoint_config.target_address,
                "target_port": data.endpoint_config.target_port,
                "endpoint_path": data.endpoint_config.endpoint_path,
                "use_ssl": data.endpoint_config.use_ssl,
            })
            protocol_prefix = "https" if data.endpoint_config.use_ssl else existing.protocol_type.lower()
            update_dict["endpoint"] = (
                f"{protocol_prefix}://"
                f"{data.endpoint_config.target_address}:"
                f"{data.endpoint_config.target_port}"
                f"{data.endpoint_config.endpoint_path}"
            )
            forwarder_updated = True

        if data.forwarder_config:
            forwarder_payload: Dict[str, Any] = {}
            if data.forwarder_config.timeout is not None:
                forwarder_payload["timeout"] = data.forwarder_config.timeout
            if data.forwarder_config.retry_count is not None:
                forwarder_payload["retry_count"] = data.forwarder_config.retry_count
            if data.forwarder_config.batch_size is not None:
                forwarder_payload["batch_size"] = data.forwarder_config.batch_size
            if data.forwarder_config.compression is not None:
                forwarder_payload["compression"] = data.forwarder_config.compression

            if forwarder_payload:
                forwarder_config.update(forwarder_payload)

            if data.forwarder_config.encryption is not None:
                encryption_cfg = _normalize_encryption_config(data.forwarder_config.encryption)
                if encryption_cfg and encryption_cfg.get("enabled"):
                    forwarder_config["encryption"] = encryption_cfg
                else:
                    forwarder_config.pop("encryption", None)
            forwarder_updated = True

        if data.auth_config is not None:
            if data.auth_config.auth_type == "none":
                forwarder_config.pop("auth_config", None)
            else:
                forwarder_config["auth_config"] = {
                    "auth_type": data.auth_config.auth_type,
                    "username": data.auth_config.username,
                    "password": data.auth_config.password,
                    "token": data.auth_config.token,
                    "api_key": data.auth_config.api_key,
                    "api_key_header": data.auth_config.api_key_header,
                    "custom_headers": data.auth_config.custom_headers,
                }
            forwarder_updated = True

        if forwarder_updated:
            update_dict["forwarder_config"] = forwarder_config

        updated = await repo.update(id, **update_dict)
        await db.commit()
        await db.refresh(updated)

        # 如果目标系统正在运行，刷新Forwarder配置
        gateway_manager = get_gateway_manager()
        if gateway_manager.is_running:
            forwarder_manager = gateway_manager.data_pipeline.forwarder_manager
            target_id_str = str(id)
            if target_id_str in forwarder_manager.target_systems:
                await forwarder_manager.unregister_target_system(id)
                if updated.is_active:
                    await forwarder_manager.register_target_system(
                        _to_pipeline_response(updated)
                    )

        response = _model_to_response(updated)

        return success_response(
            data=response.model_dump(mode='json'),
            message="目标系统更新成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(
            error="更新目标系统失败",
            detail=str(e),
            code=500
        )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    删除目标系统

    返回格式: ApiResponse包装
    """
    repo = TargetSystemRepository(db)

    try:
        success = await repo.delete(id)
        if not success:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        await db.commit()

        return success_response(
            data={"id": str(id)},
            message="目标系统删除成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(
            error="删除目标系统失败",
            detail=str(e),
            code=500
        )


# 保留原有的启停控制端点
@router.post("/{id}/start")
async def start_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """启动目标系统（注册到转发管理器）"""
    repo = TargetSystemRepository(db)

    try:
        ts = await repo.get(id)

        if not ts:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        if not ts.is_active:
            return error_response(
                error="目标系统未启用",
                detail="请先启用目标系统后再启动运行",
                code=400
            )

        gateway_manager = get_gateway_manager()
        forwarder_manager = gateway_manager.data_pipeline.forwarder_manager
        target_id = str(id)

        if target_id in forwarder_manager.target_systems and target_id in forwarder_manager.forwarders:
            status_value = _compute_runtime_status(ts)
            return success_response(
                data={"id": target_id, "status": status_value},
                message=f"目标系统 {ts.name} 已经在运行"
            )

        # 确保管道已启动
        if not gateway_manager.is_running:
            await gateway_manager.start()

        target_payload = _to_pipeline_response(ts)
        await gateway_manager.register_target_system(target_payload)

        status_value = _compute_runtime_status(ts)
        return success_response(
            data={"id": target_id, "status": status_value},
            message=f"目标系统 {ts.name} 启动成功"
        )

    except Exception as e:
        return error_response(
            error="启动目标系统失败",
            detail=str(e),
            code=500
        )


@router.post("/{id}/stop")
async def stop_target_system(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """停止目标系统（从转发管理器注销）"""
    repo = TargetSystemRepository(db)

    try:
        ts = await repo.get(id)

        if not ts:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        gateway_manager = get_gateway_manager()
        forwarder_manager = gateway_manager.data_pipeline.forwarder_manager
        target_id = str(id)

        if target_id not in forwarder_manager.target_systems and target_id not in forwarder_manager.forwarders:
            return success_response(
                data={"id": target_id, "status": "disconnected"},
                message=f"目标系统 {ts.name} 已处于停止状态"
            )

        await gateway_manager.unregister_target_system(id)

        return success_response(
            data={"id": target_id, "status": "disconnected"},
            message=f"目标系统 {ts.name} 已停止"
        )

    except Exception as e:
        return error_response(
            error="停止目标系统失败",
            detail=str(e),
            code=500
        )


@router.get("/{id}/status")
async def get_target_system_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取目标系统运行状态"""
    repo = TargetSystemRepository(db)

    try:
        ts = await repo.get(id)

        if not ts:
            return error_response(
                error="目标系统不存在",
                detail=f"ID为 {id} 的目标系统不存在",
                code=404
            )

        gateway_manager = get_gateway_manager()
        forwarder_manager = gateway_manager.data_pipeline.forwarder_manager
        target_id = str(id)
        is_registered = target_id in forwarder_manager.target_systems
        has_forwarder = target_id in forwarder_manager.forwarders
        runtime_status = _compute_runtime_status(ts)

        return success_response(
            data={
                "id": target_id,
                "name": ts.name,
                "protocol_type": ts.protocol_type.upper(),
                "is_active": ts.is_active,
                "is_registered": is_registered,
                "has_forwarder": has_forwarder,
                "status": runtime_status,
                "gateway_running": gateway_manager.is_running,
                "total_messages": getattr(ts, "total_forwarded", 0),
                "failed_messages": getattr(ts, "total_failed", 0),
                "last_message_at": (
                    ts.last_forward_at.isoformat()
                    if getattr(ts, "last_forward_at", None) else None
                ),
            },
            message="获取状态成功"
        )

    except Exception as e:
        return error_response(
            error="获取状态失败",
            detail=str(e),
            code=500
        )


__all__ = ["router"]
