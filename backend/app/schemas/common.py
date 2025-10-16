"""
通用Pydantic Schemas
包含协议类型、消息状态、数据类型等通用枚举
"""
from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class ProtocolType(str, Enum):
    """协议类型枚举"""
    UDP = "UDP"
    HTTP = "HTTP"
    WEBSOCKET = "WEBSOCKET"
    MQTT = "MQTT"
    TCP = "TCP"


class MessageStatus(str, Enum):
    """消息处理状态枚举"""
    PENDING = "PENDING"        # 待处理
    PROCESSING = "PROCESSING"  # 处理中
    PROCESSED = "PROCESSED"    # 已处理
    FORWARDED = "FORWARDED"    # 已转发
    FAILED = "FAILED"         # 处理失败
    REJECTED = "REJECTED"     # 被拒绝


class FrameType(str, Enum):
    """帧类型枚举"""
    FIXED = "FIXED"          # 固定长度帧
    VARIABLE = "VARIABLE"    # 可变长度帧
    DELIMITED = "DELIMITED"  # 分隔符分帧


class DataType(str, Enum):
    """数据类型枚举"""
    INT8 = "INT8"
    UINT8 = "UINT8"
    INT16 = "INT16"
    UINT16 = "UINT16"
    INT32 = "INT32"
    UINT32 = "UINT32"
    INT64 = "INT64"
    UINT64 = "UINT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    STRING = "STRING"
    BYTES = "BYTES"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"


class ByteOrder(str, Enum):
    """字节序枚举"""
    BIG_ENDIAN = "BIG_ENDIAN"        # 大端序
    LITTLE_ENDIAN = "LITTLE_ENDIAN"  # 小端序


class ChecksumType(str, Enum):
    """校验和类型枚举"""
    NONE = "NONE"
    CRC16 = "CRC16"
    CRC32 = "CRC32"
    MD5 = "MD5"
    SHA256 = "SHA256"
    SIMPLE_SUM = "SIMPLE_SUM"


class BaseSchema(BaseModel):
    """基础Schema"""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        from_attributes=True
    )


class TimestampMixin(BaseModel):
    """时间戳混入"""
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class UUIDMixin(BaseModel):
    """UUID混入"""
    id: UUID = Field(default_factory=uuid4, description="唯一标识")


__all__ = [
    # 枚举类型
    "ProtocolType",
    "MessageStatus",
    "FrameType",
    "DataType",
    "ByteOrder",
    "ChecksumType",

    # 基础Schema
    "BaseSchema",
    "TimestampMixin",
    "UUIDMixin",
]