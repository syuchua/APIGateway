"""
帧数据解析器实现
根据帧格式定义解析二进制数据
"""
import struct
import logging
from typing import Dict, Any, List

from app.schemas.frame_schema import FrameSchemaResponse
from app.schemas.common import DataType, ByteOrder, ChecksumType

logger = logging.getLogger(__name__)


class FrameParser:
    """
    帧数据解析器

    功能：
    - 根据帧格式定义解析二进制数据
    - 支持多种数据类型（整数、浮点数、字符串）
    - 支持大端序和小端序
    - 支持缩放和偏移计算
    - 支持校验和验证（CRC16、CRC32、简单校验和）
    """

    # 数据类型到struct格式的映射
    STRUCT_FORMAT_MAP = {
        DataType.UINT8: 'B',
        DataType.INT8: 'b',
        DataType.UINT16: 'H',
        DataType.INT16: 'h',
        DataType.UINT32: 'I',
        DataType.INT32: 'i',
        DataType.UINT64: 'Q',
        DataType.INT64: 'q',
        DataType.FLOAT32: 'f',
        DataType.FLOAT64: 'd',
    }

    def __init__(self, schema: FrameSchemaResponse):
        """
        初始化帧解析器

        Args:
            schema: 帧格式定义
        """
        self.schema = schema

    def parse(self, raw_data: bytes) -> Dict[str, Any]:
        """
        解析单个帧数据

        Args:
            raw_data: 原始二进制数据

        Returns:
            解析后的字段字典

        Raises:
            ValueError: 数据长度不足或校验失败
        """
        # 验证数据长度
        if len(raw_data) < self.schema.total_length:
            raise ValueError(
                f"数据长度不足: 期望 {self.schema.total_length} 字节, "
                f"实际 {len(raw_data)} 字节"
            )

        # 校验和验证
        if self.schema.checksum_type != ChecksumType.NONE:
            if not self._validate_checksum(raw_data):
                raise ValueError("校验失败")

        # 解析所有字段
        result = {}
        for field in self.schema.fields:
            try:
                value = self._parse_field(raw_data, field)
                result[field.name] = value
            except Exception as e:
                logger.error(f"解析字段 {field.name} 失败: {e}")
                raise

        return result

    def parse_batch(self, frames_data: List[bytes]) -> List[Dict[str, Any]]:
        """
        批量解析帧数据

        Args:
            frames_data: 原始数据列表

        Returns:
            解析结果列表
        """
        results = []
        for data in frames_data:
            try:
                result = self.parse(data)
                results.append(result)
            except Exception as e:
                logger.error(f"批量解析失败: {e}")
                raise

        return results

    def _parse_field(self, raw_data: bytes, field) -> Any:
        """
        解析单个字段

        Args:
            raw_data: 原始数据
            field: 字段定义

        Returns:
            解析后的值
        """
        # 提取字段数据
        field_data = raw_data[field.offset:field.offset + field.length]

        # 字符串类型特殊处理
        if field.data_type == DataType.STRING:
            # 去除尾部的空字节
            value = field_data.rstrip(b'\x00').decode('utf-8', errors='ignore')
            return value

        # 获取struct格式
        struct_format = self.STRUCT_FORMAT_MAP.get(field.data_type)
        if not struct_format:
            raise ValueError(f"不支持的数据类型: {field.data_type}")

        # 确定字节序
        if field.byte_order == ByteOrder.BIG_ENDIAN:
            endian = '>'
        elif field.byte_order == ByteOrder.LITTLE_ENDIAN:
            endian = '<'
        else:
            endian = '='  # 本机字节序

        # 解析数据
        format_str = f"{endian}{struct_format}"
        value = struct.unpack(format_str, field_data)[0]

        # 应用缩放和偏移
        if field.scale is not None:
            value = value * field.scale

        if field.offset_value is not None:
            value = value + field.offset_value

        return value

    def _validate_checksum(self, raw_data: bytes) -> bool:
        """
        验证校验和

        Args:
            raw_data: 原始数据

        Returns:
            校验是否通过
        """
        if self.schema.checksum_type == ChecksumType.NONE:
            return True

        if self.schema.checksum_offset is None or self.schema.checksum_length is None:
            logger.warning("校验配置不完整")
            return True

        # 提取校验和字段
        checksum_data = raw_data[
            self.schema.checksum_offset:
            self.schema.checksum_offset + self.schema.checksum_length
        ]
        expected_checksum = int.from_bytes(checksum_data, byteorder='big')

        # 计算校验和（不包括校验和字段本身）
        data_to_check = raw_data[:self.schema.checksum_offset]

        if self.schema.checksum_type == ChecksumType.CRC16:
            calculated_checksum = self._calculate_crc16(data_to_check)
        elif self.schema.checksum_type == ChecksumType.CRC32:
            calculated_checksum = self._calculate_crc32(data_to_check)
        elif self.schema.checksum_type == ChecksumType.CHECKSUM:
            calculated_checksum = self._calculate_simple_checksum(data_to_check)
        else:
            logger.warning(f"不支持的校验类型: {self.schema.checksum_type}")
            return True

        return calculated_checksum == expected_checksum

    def _calculate_crc16(self, data: bytes) -> int:
        """
        计算CRC16校验和 (MODBUS)

        Args:
            data: 要计算校验和的数据

        Returns:
            CRC16值
        """
        crc = 0xFFFF

        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1

        return crc

    def _calculate_crc32(self, data: bytes) -> int:
        """
        计算CRC32校验和

        Args:
            data: 要计算校验和的数据

        Returns:
            CRC32值
        """
        import zlib
        return zlib.crc32(data) & 0xFFFFFFFF

    def _calculate_simple_checksum(self, data: bytes) -> int:
        """
        计算简单校验和（所有字节求和）

        Args:
            data: 要计算校验和的数据

        Returns:
            校验和值
        """
        return sum(data) & 0xFF
