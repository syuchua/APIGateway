"""
数据转换器测试用例
采用TDD方法测试数据转换功能
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.core.gateway.pipeline.transformer import DataTransformer, TransformConfig
from app.schemas.common import ProtocolType


class TestTransformConfig:
    """测试转换配置"""

    def test_create_basic_config(self):
        """测试创建基本配置"""
        config = TransformConfig(
            field_mapping={
                "temperature": "temp",
                "humidity": "hum"
            }
        )

        assert config.field_mapping["temperature"] == "temp"
        assert config.field_mapping["humidity"] == "hum"
        assert config.remove_fields == []
        assert config.add_fields == {}

    def test_create_full_config(self):
        """测试创建完整配置"""
        config = TransformConfig(
            field_mapping={
                "parsed_data.temperature": "sensor.temp",
                "parsed_data.humidity": "sensor.hum"
            },
            remove_fields=["raw_data", "message_id"],
            add_fields={
                "device_type": "temperature_sensor",
                "version": "1.0"
            },
            flatten_parsed_data=True
        )

        assert config.flatten_parsed_data is True
        assert "raw_data" in config.remove_fields
        assert config.add_fields["device_type"] == "temperature_sensor"


class TestDataTransformer:
    """测试数据转换器"""

    def test_transformer_initialization(self):
        """测试转换器初始化"""
        config = TransformConfig()
        transformer = DataTransformer(config)

        assert transformer.config == config

    def test_simple_field_mapping(self):
        """测试简单字段映射"""
        config = TransformConfig(
            field_mapping={
                "temperature": "temp",
                "humidity": "hum"
            }
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "temperature": 25.5,
            "humidity": 60.0
        }

        result = transformer.transform(input_data)

        # 验证字段被映射
        assert result["temp"] == 25.5
        assert result["hum"] == 60.0
        # 未映射的字段保留
        assert result["message_id"] == "test-123"
        # 原字段被移除
        assert "temperature" not in result
        assert "humidity" not in result

    def test_nested_field_mapping(self):
        """测试嵌套字段映射"""
        config = TransformConfig(
            field_mapping={
                "parsed_data.temperature": "sensor.temp",
                "parsed_data.humidity": "sensor.hum"
            }
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0,
                "status": 1
            }
        }

        result = transformer.transform(input_data)

        # 验证嵌套字段被映射
        assert result["sensor"]["temp"] == 25.5
        assert result["sensor"]["hum"] == 60.0
        # 未映射的嵌套字段保留
        assert result["parsed_data"]["status"] == 1

    def test_flatten_parsed_data(self):
        """测试展平parsed_data"""
        config = TransformConfig(
            flatten_parsed_data=True
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "source_protocol": "UDP",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0,
                "status": 1
            }
        }

        result = transformer.transform(input_data)

        # 验证parsed_data被展平到根级别
        assert result["temperature"] == 25.5
        assert result["humidity"] == 60.0
        assert result["status"] == 1
        assert "parsed_data" not in result
        # 其他字段保留
        assert result["message_id"] == "test-123"
        assert result["source_protocol"] == "UDP"

    def test_remove_fields(self):
        """测试移除字段"""
        config = TransformConfig(
            remove_fields=["raw_data", "internal_id", "timestamp"]
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "raw_data": b"binary data",
            "internal_id": "internal-456",
            "timestamp": "2024-01-01T12:00:00",
            "temperature": 25.5
        }

        result = transformer.transform(input_data)

        # 验证字段被移除
        assert "raw_data" not in result
        assert "internal_id" not in result
        assert "timestamp" not in result
        # 其他字段保留
        assert result["message_id"] == "test-123"
        assert result["temperature"] == 25.5

    def test_add_fields(self):
        """测试添加字段"""
        config = TransformConfig(
            add_fields={
                "device_type": "temperature_sensor",
                "version": "1.0",
                "timestamp": lambda: datetime.now().isoformat()
            }
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "temperature": 25.5
        }

        result = transformer.transform(input_data)

        # 验证字段被添加
        assert result["device_type"] == "temperature_sensor"
        assert result["version"] == "1.0"
        assert "timestamp" in result
        # 原有字段保留
        assert result["message_id"] == "test-123"
        assert result["temperature"] == 25.5

    def test_combined_transformations(self):
        """测试组合转换"""
        config = TransformConfig(
            field_mapping={
                "parsed_data.temperature": "data.temp",
                "parsed_data.humidity": "data.hum"
            },
            remove_fields=["raw_data", "message_id"],
            add_fields={
                "device_type": "sensor",
                "timestamp": "2024-01-01T12:00:00"
            },
            flatten_parsed_data=False
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "source_protocol": "UDP",
            "raw_data": b"data",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0,
                "status": 1
            }
        }

        result = transformer.transform(input_data)

        # 验证字段映射
        assert result["data"]["temp"] == 25.5
        assert result["data"]["hum"] == 60.0
        # 验证字段移除
        assert "raw_data" not in result
        assert "message_id" not in result
        # 验证字段添加
        assert result["device_type"] == "sensor"
        assert result["timestamp"] == "2024-01-01T12:00:00"
        # 验证保留字段
        assert result["source_protocol"] == "UDP"
        assert result["parsed_data"]["status"] == 1

    def test_batch_transform(self):
        """测试批量转换"""
        config = TransformConfig(
            field_mapping={"temperature": "temp"}
        )
        transformer = DataTransformer(config)

        input_list = [
            {"message_id": f"msg-{i}", "temperature": 20.0 + i}
            for i in range(5)
        ]

        results = transformer.transform_batch(input_list)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["message_id"] == f"msg-{i}"
            assert result["temp"] == 20.0 + i
            assert "temperature" not in result

    def test_no_transformation(self):
        """测试无转换配置"""
        config = TransformConfig()
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "temperature": 25.5
        }

        result = transformer.transform(input_data)

        # 验证数据不变（除了bytes字段）
        assert result["message_id"] == input_data["message_id"]
        assert result["temperature"] == input_data["temperature"]

    def test_sanitize_bytes_fields(self):
        """测试自动清理bytes类型字段"""
        config = TransformConfig()
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "raw_data": b"\x01\x02\x03\x04",  # 应该被移除
            "binary": b"\xff\xfe",  # 应该被移除
            "temperature": 25.5,
            "nested": {
                "some_bytes": b"\x00\x11",  # 应该被移除
                "value": 100
            }
        }

        result = transformer.transform(input_data)

        # 验证所有bytes字段被移除
        assert "raw_data" not in result
        assert "binary" not in result
        assert "some_bytes" not in result.get("nested", {})
        # 验证其他字段保留
        assert result["message_id"] == "test-123"
        assert result["temperature"] == 25.5
        assert result["nested"]["value"] == 100

    def test_sanitize_bytes_in_lists(self):
        """测试列表中bytes字段的清理"""
        config = TransformConfig()
        transformer = DataTransformer(config)

        input_data = {
            "items": [
                {"id": 1, "data": b"\x01\x02"},
                {"id": 2, "data": b"\x03\x04"}
            ]
        }

        result = transformer.transform(input_data)

        # 验证列表中的bytes字段被移除
        for item in result["items"]:
            assert "data" not in item
            assert "id" in item

    def test_handle_missing_fields(self):
        """测试处理缺失字段"""
        config = TransformConfig(
            field_mapping={
                "nonexistent.field": "output.field"
            }
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "temperature": 25.5
        }

        result = transformer.transform(input_data)

        # 验证不会因为缺失字段而报错
        assert result["message_id"] == "test-123"
        assert result["temperature"] == 25.5
        # 缺失的映射被忽略
        assert "output" not in result or "field" not in result.get("output", {})

    def test_preserve_data_types(self):
        """测试保留数据类型"""
        config = TransformConfig(
            field_mapping={"value": "new_value"}
        )
        transformer = DataTransformer(config)

        input_data = {
            "int_value": 123,
            "float_value": 45.67,
            "str_value": "hello",
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"}
        }

        result = transformer.transform(input_data)

        # 验证数据类型保持不变
        assert isinstance(result["int_value"], int)
        assert isinstance(result["float_value"], float)
        assert isinstance(result["str_value"], str)
        assert isinstance(result["bool_value"], bool)
        assert isinstance(result["list_value"], list)
        assert isinstance(result["dict_value"], dict)


class TestDataTransformerIntegration:
    """测试数据转换器集成场景"""

    def test_transform_for_http_api(self):
        """测试转换为HTTP API格式"""
        # 模拟转换为RESTful API需要的格式
        config = TransformConfig(
            field_mapping={
                "parsed_data.temperature": "sensor_data.temperature",
                "parsed_data.humidity": "sensor_data.humidity",
                "source_address": "device_ip"
            },
            remove_fields=["raw_data", "message_id", "timestamp"],
            add_fields={
                "api_version": "v1",
                "data_type": "sensor_reading"
            },
            flatten_parsed_data=False
        )
        transformer = DataTransformer(config)

        input_data = {
            "message_id": "test-123",
            "timestamp": "2024-01-01T12:00:00",
            "source_protocol": "UDP",
            "source_address": "192.168.1.100",
            "raw_data": b"binary",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0,
                "status": 1
            }
        }

        result = transformer.transform(input_data)

        # 验证转换后的格式适合HTTP API
        assert result["sensor_data"]["temperature"] == 25.5
        assert result["sensor_data"]["humidity"] == 60.0
        assert result["device_ip"] == "192.168.1.100"
        assert result["api_version"] == "v1"
        assert result["data_type"] == "sensor_reading"
        assert "raw_data" not in result
        assert "message_id" not in result

    def test_transform_for_time_series_db(self):
        """测试转换为时序数据库格式"""
        # 模拟转换为InfluxDB格式
        config = TransformConfig(
            flatten_parsed_data=True,
            remove_fields=["source_protocol", "raw_data"],
            add_fields={
                "measurement": "temperature",
                "tags": {
                    "location": "room1",
                    "sensor_type": "DHT22"
                }
            }
        )
        transformer = DataTransformer(config)

        input_data = {
            "timestamp": "2024-01-01T12:00:00",
            "source_protocol": "UDP",
            "raw_data": b"data",
            "parsed_data": {
                "temperature": 25.5,
                "humidity": 60.0
            }
        }

        result = transformer.transform(input_data)

        # 验证时序数据库格式
        assert result["measurement"] == "temperature"
        assert result["tags"]["location"] == "room1"
        assert result["temperature"] == 25.5
        assert result["humidity"] == 60.0
        assert "parsed_data" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
