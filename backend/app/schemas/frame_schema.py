"""
帧格式相关Pydantic Schemas
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import Field

from .common import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    FrameType,
    DataType,
    ByteOrder,
    ChecksumType
)


class FieldDefinition(BaseSchema):
    """字段定义Schema"""
    name: str = Field(..., description="字段名称")
    data_type: DataType = Field(..., description="数据类型")
    offset: int = Field(..., ge=0, description="字段偏移量（字节）")
    length: int = Field(..., ge=0, description="字段长度（字节，0表示可变长度）")
    byte_order: ByteOrder = Field(default=ByteOrder.BIG_ENDIAN, description="字节序")
    scale: float = Field(default=1.0, description="缩放因子")
    offset_value: float = Field(default=0.0, description="偏移值")
    description: Optional[str] = Field(None, description="字段描述")


class FrameSchemaCreate(BaseSchema):
    """创建帧格式Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="帧格式名称")
    description: Optional[str] = Field(None, description="帧格式描述")
    version: str = Field(default="1.0.0", description="版本号")

    # 帧结构
    frame_type: FrameType = Field(..., description="帧类型")
    total_length: Optional[int] = Field(None, ge=1, description="总长度（固定长度帧）")
    header_length: int = Field(default=0, ge=0, description="帧头长度")
    delimiter: Optional[str] = Field(None, description="分隔符（分隔符分帧）")

    # 字段定义
    fields: List[FieldDefinition] = Field(..., min_length=1, description="字段定义列表")

    # 校验设置
    checksum_type: ChecksumType = Field(default=ChecksumType.NONE, description="校验和类型")
    checksum_offset: Optional[int] = Field(None, description="校验和字段偏移")
    checksum_length: Optional[int] = Field(None, description="校验和字段长度")


class FrameSchemaUpdate(BaseSchema):
    """更新帧格式Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="帧格式名称")
    description: Optional[str] = Field(None, description="帧格式描述")
    version: Optional[str] = Field(None, description="版本号")
    frame_type: Optional[FrameType] = Field(None, description="帧类型")
    total_length: Optional[int] = Field(None, ge=1, description="总长度")
    fields: Optional[List[FieldDefinition]] = Field(None, description="字段定义列表")
    is_published: Optional[bool] = Field(None, description="是否已发布")
    is_active: Optional[bool] = Field(None, description="是否激活")


class FrameSchemaResponse(UUIDMixin, TimestampMixin, BaseSchema):
    """帧格式响应Schema"""
    name: str
    description: Optional[str]
    version: str
    frame_type: FrameType
    total_length: Optional[int]
    header_length: int
    delimiter: Optional[str]
    fields: List[FieldDefinition]
    checksum_type: ChecksumType
    checksum_offset: Optional[int]
    checksum_length: Optional[int]
    is_published: bool
    is_active: bool


__all__ = [
    "FieldDefinition",
    "FrameSchemaCreate",
    "FrameSchemaUpdate",
    "FrameSchemaResponse",
]