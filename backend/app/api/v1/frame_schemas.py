"""
帧格式管理API
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.frame_schema import FrameSchemaRepository
from app.schemas.frame_schema import (
    FrameSchemaCreate,
    FrameSchemaUpdate,
    FrameSchemaResponse,
)

router = APIRouter()


@router.post("/", response_model=FrameSchemaResponse, status_code=status.HTTP_201_CREATED)
async def create_frame_schema(
    data: FrameSchemaCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建帧格式"""
    repo = FrameSchemaRepository(db)

    # 检查名称+版本是否已存在
    existing = await repo.get_by_name_version(data.name, data.version)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"帧格式 {data.name} 版本 {data.version} 已存在"
        )

    # 转换fields为dict列表
    fields_data = [field.model_dump() for field in data.fields]

    # 转换checksum
    checksum_data = None
    if data.checksum_type.value != "none":
        checksum_data = {
            "type": data.checksum_type.value,
            "offset": data.checksum_offset,
            "length": data.checksum_length,
        }

    fs = await repo.create(
        name=data.name,
        version=data.version,
        description=data.description,
        protocol_type=data.frame_type.value,  # 注意这里使用frame_type
        frame_type=data.frame_type.value,
        total_length=data.total_length,
        fields=fields_data,
        checksum=checksum_data,
        is_published=False,
    )

    await db.commit()
    return FrameSchemaResponse(**fs.to_dict())


@router.get("/", response_model=List[FrameSchemaResponse])
async def list_frame_schemas(
    skip: int = 0,
    limit: int = 100,
    is_published: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """获取帧格式列表"""
    repo = FrameSchemaRepository(db)

    filters = {}
    if is_published is not None:
        filters["is_published"] = is_published

    schemas = await repo.get_all(skip=skip, limit=limit, **filters)
    return [FrameSchemaResponse(**fs.to_dict()) for fs in schemas]


@router.get("/{id}", response_model=FrameSchemaResponse)
async def get_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取帧格式详情"""
    repo = FrameSchemaRepository(db)
    fs = await repo.get(id)

    if not fs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"帧格式 {id} 不存在"
        )

    return FrameSchemaResponse(**fs.to_dict())


@router.put("/{id}", response_model=FrameSchemaResponse)
async def update_frame_schema(
    id: UUID,
    data: FrameSchemaUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新帧格式"""
    repo = FrameSchemaRepository(db)

    # 检查是否存在
    existing = await repo.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"帧格式 {id} 不存在"
        )

    # 构建更新数据
    update_data = data.model_dump(exclude_unset=True)

    # 处理fields
    if "fields" in update_data:
        update_data["fields"] = [field.model_dump() if hasattr(field, 'model_dump') else field for field in update_data["fields"]]

    # 处理frame_type
    if "frame_type" in update_data:
        update_data["frame_type"] = update_data["frame_type"].value

    updated = await repo.update(id, **update_data)
    await db.commit()

    return FrameSchemaResponse(**updated.to_dict())


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除帧格式"""
    repo = FrameSchemaRepository(db)

    success = await repo.delete(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"帧格式 {id} 不存在"
        )

    await db.commit()


@router.post("/{id}/publish", response_model=FrameSchemaResponse)
async def publish_frame_schema(
    id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """发布帧格式"""
    repo = FrameSchemaRepository(db)

    success = await repo.publish(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"帧格式 {id} 不存在"
        )

    await db.commit()

    # 获取更新后的帧格式
    fs = await repo.get(id)
    return FrameSchemaResponse(**fs.to_dict())


__all__ = ["router"]
