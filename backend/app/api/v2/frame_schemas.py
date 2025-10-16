"""
帧格式管理 API v2
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.frame_schema import FrameSchemaRepository
from app.models.frame_schema import FrameSchema
from app.schemas.common import ChecksumType, FrameType, ProtocolType
from app.schemas.frame_schema_v2 import (
    FrameChecksumConfig,
    FrameFieldConfig,
    FrameSchemaCreateV2,
    FrameSchemaResponseV2,
    FrameSchemaUpdateV2,
)
from app.schemas.response import error_response, paginated_response, success_response

router = APIRouter()


def _serialize_checksum(checksum: Optional[FrameChecksumConfig]) -> Optional[Dict[str, Any]]:
    if checksum is None:
        return None
    if checksum.type == ChecksumType.NONE:
        return None
    data = checksum.model_dump(mode="json", exclude_none=True)
    return data


def _deserialize_checksum(raw: Optional[Dict[str, Any]]) -> Optional[FrameChecksumConfig]:
    if not raw:
        return None
    checksum_type = raw.get("type") or raw.get("checksum_type") or ChecksumType.NONE.value
    try:
        checksum_enum = ChecksumType(str(checksum_type).upper())
    except ValueError:
        checksum_enum = ChecksumType.NONE
    return FrameChecksumConfig(
        type=checksum_enum,
        offset=raw.get("offset") or raw.get("checksum_offset"),
        length=raw.get("length") or raw.get("checksum_length"),
    )


def _deserialize_fields(raw_fields: Optional[List[Dict[str, Any]]]) -> List[FrameFieldConfig]:
    if not raw_fields:
        return []
    fields: List[FrameFieldConfig] = []
    for field in raw_fields:
        fields.append(FrameFieldConfig(**field))
    return fields


def _model_to_response(fs: FrameSchema) -> FrameSchemaResponseV2:
    protocol_value = fs.protocol_type.upper() if fs.protocol_type else ProtocolType.UDP.value
    frame_type_value = fs.frame_type.upper() if fs.frame_type else FrameType.FIXED.value
    protocol = ProtocolType(protocol_value)
    frame_type = FrameType(frame_type_value)

    checksum_cfg = _deserialize_checksum(fs.checksum)
    fields_cfg = _deserialize_fields(fs.fields)

    return FrameSchemaResponseV2(
        id=fs.id,
        name=fs.name,
        description=fs.description,
        version=fs.version,
        protocol_type=protocol,
        frame_type=frame_type,
        total_length=fs.total_length,
        fields=fields_cfg,
        checksum=checksum_cfg,
        is_published=fs.is_published,
        created_at=fs.created_at,
        updated_at=fs.updated_at,
    )


def _normalize_protocol_value(protocol: ProtocolType | str) -> str:
    if isinstance(protocol, ProtocolType):
        return protocol.value.lower()
    return str(protocol).lower()


def _normalize_frame_type_value(frame_type: FrameType | str) -> str:
    if isinstance(frame_type, FrameType):
        return frame_type.value.lower()
    return str(frame_type).lower()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_frame_schema(
    payload: FrameSchemaCreateV2,
    db: AsyncSession = Depends(get_db),
):
    """创建帧格式"""
    repo = FrameSchemaRepository(db)

    existing = await repo.get_by_name_version(payload.name, payload.version)
    if existing:
        return error_response(
            error="帧格式已存在",
            detail=f"{payload.name} v{payload.version} 已存在",
            code=400,
        )

    fields_data = [field.model_dump(mode="json") for field in payload.fields]
    checksum_data = _serialize_checksum(payload.checksum)

    fs = await repo.create(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        protocol_type=_normalize_protocol_value(payload.protocol_type),
        frame_type=_normalize_frame_type_value(payload.frame_type),
        total_length=payload.total_length,
        fields=fields_data,
        checksum=checksum_data,
        is_published=payload.is_published,
    )

    await db.commit()
    await db.refresh(fs)

    response = _model_to_response(fs)
    return success_response(
        data=response.model_dump(mode="json"),
        message="帧格式创建成功",
        code=201,
    )


@router.get("/")
async def list_frame_schemas(
    page: int = 1,
    limit: int = 20,
    protocol_type: Optional[ProtocolType] = None,
    is_published: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """分页获取帧格式列表"""
    if page < 1:
        return error_response(error="参数错误", detail="page 必须大于等于 1", code=400)
    if limit < 1 or limit > 100:
        return error_response(error="参数错误", detail="limit 必须在 1-100 之间", code=400)

    repo = FrameSchemaRepository(db)
    skip = (page - 1) * limit
    filters: Dict[str, Any] = {}
    if protocol_type is not None:
        filters["protocol_type"] = _normalize_protocol_value(protocol_type)
    if is_published is not None:
        filters["is_published"] = is_published

    schemas = await repo.get_all(skip=skip, limit=limit, **filters)
    total = await repo.count(**filters)
    items = [_model_to_response(fs).model_dump(mode="json") for fs in schemas]

    return paginated_response(
        items=items,
        page=page,
        limit=limit,
        total=total,
        message="获取帧格式列表成功",
    )


@router.get("/{id}")
async def get_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取帧格式详情"""
    repo = FrameSchemaRepository(db)
    fs = await repo.get(id)
    if not fs:
        return error_response(
            error="帧格式不存在",
            detail=f"ID 为 {id} 的帧格式不存在",
            code=404,
        )

    response = _model_to_response(fs)
    return success_response(
        data=response.model_dump(mode="json"),
        message="获取帧格式详情成功",
    )


@router.put("/{id}")
async def update_frame_schema(
    id: UUID,
    payload: FrameSchemaUpdateV2,
    db: AsyncSession = Depends(get_db),
):
    """更新帧格式"""
    repo = FrameSchemaRepository(db)
    existing = await repo.get(id)
    if not existing:
        return error_response(
            error="帧格式不存在",
            detail=f"ID 为 {id} 的帧格式不存在",
            code=404,
        )

    update_dict: Dict[str, Any] = {}
    if payload.name is not None:
        update_dict["name"] = payload.name
    if payload.description is not None:
        update_dict["description"] = payload.description
    if payload.version is not None:
        update_dict["version"] = payload.version
    if payload.protocol_type is not None:
        update_dict["protocol_type"] = _normalize_protocol_value(payload.protocol_type)
    if payload.frame_type is not None:
        update_dict["frame_type"] = _normalize_frame_type_value(payload.frame_type)
    if payload.total_length is not None:
        update_dict["total_length"] = payload.total_length
    if payload.fields is not None:
        update_dict["fields"] = [field.model_dump(mode="json") for field in payload.fields]
    if payload.checksum is not None:
        update_dict["checksum"] = _serialize_checksum(payload.checksum)
    if payload.is_published is not None:
        update_dict["is_published"] = payload.is_published

    updated = await repo.update(id, **update_dict)
    await db.commit()
    await db.refresh(updated)

    response = _model_to_response(updated)
    return success_response(
        data=response.model_dump(mode="json"),
        message="帧格式更新成功",
    )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除帧格式"""
    repo = FrameSchemaRepository(db)
    success = await repo.delete(id)
    if not success:
        return error_response(
            error="帧格式不存在",
            detail=f"ID 为 {id} 的帧格式不存在",
            code=404,
        )

    await db.commit()
    return success_response(
        data={"id": str(id)},
        message="帧格式已删除",
    )


@router.post("/{id}/publish")
async def publish_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """发布帧格式"""
    repo = FrameSchemaRepository(db)
    success = await repo.publish(id)
    if not success:
        return error_response(
            error="帧格式不存在",
            detail=f"ID 为 {id} 的帧格式不存在",
            code=404,
        )

    await db.commit()
    fs = await repo.get(id)
    response = _model_to_response(fs)
    return success_response(
        data=response.model_dump(mode="json"),
        message="帧格式已发布",
    )


__all__ = ["router"]
