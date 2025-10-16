"""
帧解析器测试用例
采用TDD方法测试帧数据解析功能
"""
import pytest
import struct
from uuid import uuid4

from app.core.gateway.frame.parser import FrameParser
from app.schemas.frame_schema import FieldDefinition, FrameSchemaResponse
from app.schemas.common import FrameType, DataType, ByteOrder, ChecksumType
from datetime import datetime


class TestFrameParser:
    """测试帧解析器"""

    @pytest.fixture
    def simple_frame_schema(self):
        """创建简单的固定长度帧格式"""
        return FrameSchemaResponse(
            id=uuid4(),
            name="简单传感器帧",
            description="8字节固定长度帧",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="device_id",
                    data_type=DataType.UINT16,
                    offset=0,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN
                ),
                FieldDefinition(
                    name="temperature",
                    data_type=DataType.INT16,
                    offset=2,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN,
                    scale=0.1,
                    offset_value=-40.0
                ),
                FieldDefinition(
                    name="humidity",
                    data_type=DataType.UINT16,
                    offset=4,
                    length=2,
                    byte_order=ByteOrder.BIG_ENDIAN,
                    scale=0.1
                ),
                FieldDefinition(
                    name="status",
                    data_type=DataType.UINT8,
                    offset=6,
                    length=1,
                    byte_order=ByteOrder.BIG_ENDIAN
                )
            ],
            checksum_type=ChecksumType.NONE,
            checksum_offset=None,
            checksum_length=None,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def test_parse_fixed_length_frame(self, simple_frame_schema):
        """测试解析固定长度帧"""
        parser = FrameParser(simple_frame_schema)

        # 构造测试数据: device_id=100, temp=25.5°C, humidity=60.5%, status=1
        # temperature原始值 = (25.5 + 40) / 0.1 = 655
        # humidity原始值 = 60.5 / 0.1 = 605
        raw_data = struct.pack('>HHHB', 100, 655, 605, 1) + b'\x00'

        result = parser.parse(raw_data)

        assert result["device_id"] == 100
        assert abs(result["temperature"] - 25.5) < 0.01
        assert abs(result["humidity"] - 60.5) < 0.01
        assert result["status"] == 1

    def test_parse_with_scale_and_offset(self, simple_frame_schema):
        """测试缩放和偏移计算"""
        parser = FrameParser(simple_frame_schema)

        # temperature = -10°C, 原始值 = (-10 + 40) / 0.1 = 300
        raw_data = struct.pack('>HHHB', 200, 300, 500, 0) + b'\x00'

        result = parser.parse(raw_data)

        assert abs(result["temperature"] - (-10.0)) < 0.01

    def test_parse_little_endian(self):
        """测试小端序解析"""
        schema = FrameSchemaResponse(
            id=uuid4(),
            name="小端序帧",
            description="测试小端序",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=4,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="value",
                    data_type=DataType.UINT32,
                    offset=0,
                    length=4,
                    byte_order=ByteOrder.LITTLE_ENDIAN
                )
            ],
            checksum_type=ChecksumType.NONE,
            checksum_offset=None,
            checksum_length=None,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        parser = FrameParser(schema)
        raw_data = struct.pack('<I', 0x12345678)

        result = parser.parse(raw_data)

        assert result["value"] == 0x12345678

    def test_parse_float_types(self):
        """测试浮点数类型解析"""
        schema = FrameSchemaResponse(
            id=uuid4(),
            name="浮点数帧",
            description="测试浮点数",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="float32_value",
                    data_type=DataType.FLOAT32,
                    offset=0,
                    length=4,
                    byte_order=ByteOrder.BIG_ENDIAN
                ),
                FieldDefinition(
                    name="float64_value",
                    data_type=DataType.FLOAT64,
                    offset=4,
                    length=8,
                    byte_order=ByteOrder.BIG_ENDIAN
                )
            ],
            checksum_type=ChecksumType.NONE,
            checksum_offset=None,
            checksum_length=None,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        parser = FrameParser(schema)
        raw_data = struct.pack('>fd', 3.14159, 2.718281828)

        result = parser.parse(raw_data)

        assert abs(result["float32_value"] - 3.14159) < 0.0001
        assert abs(result["float64_value"] - 2.718281828) < 0.00001

    def test_parse_invalid_frame_length(self, simple_frame_schema):
        """测试无效帧长度"""
        parser = FrameParser(simple_frame_schema)

        # 数据太短
        raw_data = b'\x00\x01\x02'

        with pytest.raises(ValueError, match="数据长度不足"):
            parser.parse(raw_data)

    def test_parse_string_field(self):
        """测试字符串字段解析"""
        schema = FrameSchemaResponse(
            id=uuid4(),
            name="字符串帧",
            description="包含字符串字段",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=20,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="device_name",
                    data_type=DataType.STRING,
                    offset=0,
                    length=16,
                    byte_order=ByteOrder.BIG_ENDIAN
                ),
                FieldDefinition(
                    name="status",
                    data_type=DataType.UINT32,
                    offset=16,
                    length=4,
                    byte_order=ByteOrder.BIG_ENDIAN
                )
            ],
            checksum_type=ChecksumType.NONE,
            checksum_offset=None,
            checksum_length=None,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        parser = FrameParser(schema)
        raw_data = b"SENSOR_001\x00\x00\x00\x00\x00\x00" + struct.pack('>I', 100)

        result = parser.parse(raw_data)

        assert result["device_name"] == "SENSOR_001"
        assert result["status"] == 100

    def test_parse_with_crc16_checksum(self):
        """测试CRC16校验"""
        schema = FrameSchemaResponse(
            id=uuid4(),
            name="带CRC16校验的帧",
            description="测试CRC16",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=8,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="data",
                    data_type=DataType.UINT32,
                    offset=0,
                    length=4,
                    byte_order=ByteOrder.BIG_ENDIAN
                )
            ],
            checksum_type=ChecksumType.CRC16,
            checksum_offset=6,
            checksum_length=2,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        parser = FrameParser(schema)

        # 构造带正确CRC的数据
        data = struct.pack('>I', 0x12345678) + b'\x00\x00'
        crc = parser._calculate_crc16(data[:6])
        raw_data = data[:6] + struct.pack('>H', crc)

        result = parser.parse(raw_data)

        assert result["data"] == 0x12345678

    def test_parse_invalid_checksum(self):
        """测试校验失败"""
        schema = FrameSchemaResponse(
            id=uuid4(),
            name="带校验的帧",
            description="测试校验失败",
            version="1.0.0",
            frame_type=FrameType.FIXED,
            total_length=6,
            header_length=0,
            delimiter=None,
            fields=[
                FieldDefinition(
                    name="data",
                    data_type=DataType.UINT32,
                    offset=0,
                    length=4,
                    byte_order=ByteOrder.BIG_ENDIAN
                )
            ],
            checksum_type=ChecksumType.CRC16,
            checksum_offset=4,
            checksum_length=2,
            is_published=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        parser = FrameParser(schema)

        # 使用错误的CRC
        raw_data = struct.pack('>I', 0x12345678) + struct.pack('>H', 0xFFFF)

        with pytest.raises(ValueError, match="校验失败"):
            parser.parse(raw_data)

    def test_parse_batch(self, simple_frame_schema):
        """测试批量解析"""
        parser = FrameParser(simple_frame_schema)

        frames_data = [
            struct.pack('>HHHB', 100, 655, 605, 1) + b'\x00',
            struct.pack('>HHHB', 101, 656, 606, 2) + b'\x00',
            struct.pack('>HHHB', 102, 657, 607, 3) + b'\x00',
        ]

        results = parser.parse_batch(frames_data)

        assert len(results) == 3
        assert results[0]["device_id"] == 100
        assert results[1]["device_id"] == 101
        assert results[2]["device_id"] == 102


if __name__ == "__main__":
    pytest.main([__file__, "-v"])