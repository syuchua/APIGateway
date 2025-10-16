"""
测试重构后的数据源Schema（嵌套config结构）
"""
import pytest
from uuid import uuid4
from app.schemas.data_source_v2 import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    ConnectionConfig,
    ParseConfig,
)
from app.schemas.common import ProtocolType


class TestConnectionConfig:
    """测试连接配置Schema"""

    def test_connection_config_with_all_fields(self):
        """测试包含所有字段的连接配置"""
        config = ConnectionConfig(
            listen_address="192.168.1.100",
            listen_port=9999,
            max_connections=200,
            timeout_seconds=60,
            buffer_size=16384,
        )

        assert config.listen_address == "192.168.1.100"
        assert config.listen_port == 9999
        assert config.max_connections == 200
        assert config.timeout_seconds == 60
        assert config.buffer_size == 16384

    def test_connection_config_with_defaults(self):
        """测试使用默认值的连接配置"""
        config = ConnectionConfig(
            listen_port=8080
        )

        assert config.listen_address == "0.0.0.0"
        assert config.listen_port == 8080
        assert config.max_connections == 100
        assert config.timeout_seconds == 30
        assert config.buffer_size == 8192

    def test_connection_config_validation(self):
        """测试连接配置验证"""
        # 端口范围验证
        with pytest.raises(ValueError):
            ConnectionConfig(listen_port=0)

        with pytest.raises(ValueError):
            ConnectionConfig(listen_port=70000)


class TestParseConfig:
    """测试解析配置Schema"""

    def test_parse_config_with_frame_schema(self):
        """测试使用帧格式的解析配置"""
        frame_id = uuid4()
        config = ParseConfig(
            auto_parse=True,
            frame_schema_id=frame_id,
        )

        assert config.auto_parse is True
        assert config.frame_schema_id == frame_id
        assert config.parse_options is None

    def test_parse_config_with_options(self):
        """测试使用选项的解析配置"""
        config = ParseConfig(
            auto_parse=True,
            parse_options={"encoding": "utf-8", "delimiter": "\\n"},
        )

        assert config.auto_parse is True
        assert config.parse_options["encoding"] == "utf-8"
        assert config.parse_options["delimiter"] == "\\n"


class TestDataSourceCreate:
    """测试数据源创建Schema"""

    def test_create_with_nested_config(self):
        """测试使用嵌套配置创建数据源"""
        data = DataSourceCreate(
            name="UDP Sensor",
            description="Temperature sensor",
            protocol_type=ProtocolType.UDP,
            connection_config=ConnectionConfig(
                listen_address="0.0.0.0",
                listen_port=9999,
                max_connections=50,
            ),
            parse_config=ParseConfig(
                auto_parse=True,
            ),
        )

        assert data.name == "UDP Sensor"
        assert data.protocol_type == ProtocolType.UDP
        assert data.connection_config.listen_port == 9999
        assert data.parse_config.auto_parse is True

    def test_create_with_protocol_normalization(self):
        """测试协议类型自动转换为大写"""
        data = DataSourceCreate(
            name="Test Source",
            protocol_type="udp",  # 小写输入
            connection_config=ConnectionConfig(listen_port=8080),
        )

        assert data.protocol_type == ProtocolType.UDP

    def test_create_converts_to_dict_correctly(self):
        """测试转换为字典格式正确"""
        frame_id = uuid4()
        data = DataSourceCreate(
            name="Test Source",
            protocol_type=ProtocolType.TCP,
            connection_config=ConnectionConfig(
                listen_port=5000,
                max_connections=150,
            ),
            parse_config=ParseConfig(
                auto_parse=True,
                frame_schema_id=frame_id,
            ),
        )

        data_dict = data.model_dump()

        assert data_dict["name"] == "Test Source"
        assert data_dict["protocol_type"] == "TCP"
        assert isinstance(data_dict["connection_config"], dict)
        assert data_dict["connection_config"]["listen_port"] == 5000
        assert isinstance(data_dict["parse_config"], dict)
        assert str(data_dict["parse_config"]["frame_schema_id"]) == str(frame_id)


class TestDataSourceUpdate:
    """测试数据源更新Schema"""

    def test_update_partial_fields(self):
        """测试部分字段更新"""
        data = DataSourceUpdate(
            name="Updated Name",
            connection_config=ConnectionConfig(
                listen_port=10000,
            ),
        )

        assert data.name == "Updated Name"
        assert data.connection_config.listen_port == 10000

    def test_update_with_exclude_unset(self):
        """测试排除未设置字段"""
        data = DataSourceUpdate(
            name="Updated Name",
        )

        data_dict = data.model_dump(exclude_unset=True)

        assert "name" in data_dict
        assert "connection_config" not in data_dict
        assert "parse_config" not in data_dict


class TestDataSourceResponse:
    """测试数据源响应Schema"""

    def test_response_with_nested_config(self):
        """测试响应包含嵌套配置"""
        ds_id = uuid4()
        frame_id = uuid4()

        response = DataSourceResponse(
            id=ds_id,
            name="Test Source",
            description="Test Description",
            protocol_type=ProtocolType.HTTP,
            connection_config=ConnectionConfig(
                listen_address="127.0.0.1",
                listen_port=8080,
            ),
            parse_config=ParseConfig(
                auto_parse=True,
                frame_schema_id=frame_id,
            ),
            is_active=True,
        )

        assert response.id == ds_id
        assert response.name == "Test Source"
        assert response.protocol_type == ProtocolType.HTTP
        assert response.connection_config.listen_address == "127.0.0.1"
        assert response.parse_config.frame_schema_id == frame_id

    def test_response_serialization(self):
        """测试响应序列化"""
        ds_id = uuid4()

        response = DataSourceResponse(
            id=ds_id,
            name="Test Source",
            protocol_type=ProtocolType.WEBSOCKET,
            connection_config=ConnectionConfig(listen_port=9000),
            parse_config=ParseConfig(auto_parse=False),
            is_active=True,
        )

        json_data = response.model_dump_json()

        assert isinstance(json_data, str)
        assert "Test Source" in json_data
        assert "WEBSOCKET" in json_data
        assert "9000" in json_data


class TestDataSourceSchemaCompatibility:
    """测试数据源Schema与前端兼容性"""

    def test_matches_frontend_interface(self):
        """测试匹配前端DataSource接口"""
        ds_id = uuid4()

        response = DataSourceResponse(
            id=ds_id,
            name="Frontend Compatible",
            description="Compatible with frontend",
            protocol_type=ProtocolType.UDP,
            connection_config=ConnectionConfig(
                listen_address="0.0.0.0",
                listen_port=9999,
                max_connections=100,
                timeout_seconds=30,
                buffer_size=8192,
            ),
            parse_config=ParseConfig(
                auto_parse=True,
                frame_schema_id=uuid4(),
            ),
            is_active=True,
        )

        data = response.model_dump()

        # 验证前端期望的字段都存在
        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "protocol_type" in data
        assert "connection_config" in data
        assert "parse_config" in data  # 前端的parse_rules映射
        assert "is_active" in data
        assert "created_at" in data
        assert "updated_at" in data

        # 验证嵌套结构
        assert isinstance(data["connection_config"], dict)
        assert "listen_address" in data["connection_config"]
        assert "listen_port" in data["connection_config"]
