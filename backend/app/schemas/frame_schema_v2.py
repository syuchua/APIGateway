"""
帧格式相关Pydantic Schemas (v2)
"""
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .common import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    ProtocolType,
    FrameType,
    DataType,
    ByteOrder,
    ChecksumType,
)


class FrameFieldConfig(BaseSchema):
    """帧字段配置"""

    name: str = Field(..., description="字段名称")
    data_type: DataType = Field(..., description="数据类型")
    offset: int = Field(..., ge=0, description="字段偏移量（字节）")
    length: int = Field(..., ge=0, description="字段长度（字节，0 表示可变长度）")
    byte_order: ByteOrder = Field(default=ByteOrder.BIG_ENDIAN, description="字节序")
    scale: float = Field(default=1.0, description="缩放因子")
    offset_value: float = Field(default=0.0, description="偏移值")
    description: Optional[str] = Field(None, description="字段描述")


class FrameChecksumConfig(BaseSchema):
    """帧校验配置"""

    type: ChecksumType = Field(default=ChecksumType.NONE, description="校验和类型")
    offset: Optional[int] = Field(None, ge=0, description="校验字段偏移")
    length: Optional[int] = Field(None, ge=0, description="校验字段长度")


class FrameSchemaCreateV2(BaseSchema):
    """创建帧格式（v2）"""

    name: str = Field(..., min_length=1, max_length=100, description="帧格式名称")
    description: Optional[str] = Field(None, description="帧格式描述")
    version: str = Field(default="1.0.0", description="版本号")
    protocol_type: ProtocolType = Field(..., description="协议类型（例：UDP/TCP）")
    frame_type: FrameType = Field(..., description="帧类型")
    total_length: Optional[int] = Field(None, ge=1, description="总长度（固定长度帧）")
    fields: List[FrameFieldConfig] = Field(..., min_length=1, description="字段定义列表")
    checksum: Optional[FrameChecksumConfig] = Field(None, description="校验和配置")
    is_published: bool = Field(default=False, description="是否发布")

    @field_validator("protocol_type", mode="before")
    @classmethod
    def normalize_protocol(cls, value):
        if isinstance(value, ProtocolType):
            return value
        if isinstance(value, str):
            return ProtocolType(value.upper())
        raise ValueError("不支持的协议类型")

    @field_validator("frame_type", mode="before")
    @classmethod
    def normalize_frame_type(cls, value):
        if isinstance(value, FrameType):
            return value
        if isinstance(value, str):
            return FrameType(value.upper())
        raise ValueError("不支持的帧类型")


class FrameSchemaUpdateV2(BaseSchema):
    """更新帧格式（v2）"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="帧格式名称")
    description: Optional[str] = Field(None, description="帧格式描述")
    version: Optional[str] = Field(None, description="版本号")
    protocol_type: Optional[ProtocolType] = Field(None, description="协议类型")
    frame_type: Optional[FrameType] = Field(None, description="帧类型")
    total_length: Optional[int] = Field(None, ge=1, description="总长度")
    fields: Optional[List[FrameFieldConfig]] = Field(None, description="字段定义列表")
    checksum: Optional[FrameChecksumConfig] = Field(None, description="校验和配置")
    is_published: Optional[bool] = Field(None, description="是否发布")


class FrameSchemaResponseV2(UUIDMixin, TimestampMixin, BaseSchema):
    """帧格式响应（v2）"""

    name: str
    description: Optional[str]
    version: str
    protocol_type: ProtocolType
    frame_type: FrameType
    total_length: Optional[int]
    fields: List[FrameFieldConfig]
    checksum: Optional[FrameChecksumConfig]
    is_published: bool


__all__ = [
    "FrameFieldConfig",
    "FrameChecksumConfig",
    "FrameSchemaCreateV2",
    "FrameSchemaUpdateV2",
    "FrameSchemaResponseV2",
]
