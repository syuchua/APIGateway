"""
测试重构后的目标系统Schema（嵌套config结构 + auth_config）
"""
import pytest
from uuid import uuid4
from app.schemas.target_system_v2 import (
    TargetSystemCreate,
    TargetSystemUpdate,
    TargetSystemResponse,
    EndpointConfig,
    AuthConfig,
    ForwarderConfig,
)
from app.schemas.common import ProtocolType


class TestEndpointConfig:
    """测试端点配置Schema"""

    def test_endpoint_config_http(self):
        """测试HTTP端点配置"""
        config = EndpointConfig(
            target_address="api.example.com",
            target_port=443,
            endpoint_path="/api/v1/data",
            use_ssl=True,
        )

        assert config.target_address == "api.example.com"
        assert config.target_port == 443
        assert config.endpoint_path == "/api/v1/data"
        assert config.use_ssl is True

    def test_endpoint_config_defaults(self):
        """测试端点配置默认值"""
        config = EndpointConfig(
            target_address="localhost",
            target_port=8080,
        )

        assert config.endpoint_path == "/"
        assert config.use_ssl is False


class TestAuthConfig:
    """测试认证配置Schema"""

    def test_auth_config_basic(self):
        """测试Basic认证配置"""
        config = AuthConfig(
            auth_type="basic",
            username="admin",
            password="secret123",
        )

        assert config.auth_type == "basic"
        assert config.username == "admin"
        assert config.password == "secret123"

    def test_auth_config_bearer_token(self):
        """测试Bearer Token认证"""
        config = AuthConfig(
            auth_type="bearer",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        )

        assert config.auth_type == "bearer"
        assert config.token is not None

    def test_auth_config_api_key(self):
        """测试API Key认证"""
        config = AuthConfig(
            auth_type="api_key",
            api_key="my-secret-key",
            api_key_header="X-API-Key",
        )

        assert config.auth_type == "api_key"
        assert config.api_key == "my-secret-key"
        assert config.api_key_header == "X-API-Key"

    def test_auth_config_custom(self):
        """测试自定义认证配置"""
        config = AuthConfig(
            auth_type="custom",
            custom_headers={"Authorization": "Custom token123"},
        )

        assert config.auth_type == "custom"
        assert config.custom_headers["Authorization"] == "Custom token123"


class TestForwarderConfig:
    """测试转发配置Schema"""

    def test_forwarder_config_with_all_fields(self):
        """测试包含所有字段的转发配置"""
        config = ForwarderConfig(
            timeout=60,
            retry_count=5,
            batch_size=100,
            compression=True,
        )

        assert config.timeout == 60
        assert config.retry_count == 5
        assert config.batch_size == 100
        assert config.compression is True

    def test_forwarder_config_defaults(self):
        """测试转发配置默认值"""
        config = ForwarderConfig()

        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.batch_size == 1
        assert config.compression is False


class TestTargetSystemCreate:
    """测试目标系统创建Schema"""

    def test_create_with_nested_configs(self):
        """测试使用嵌套配置创建目标系统"""
        data = TargetSystemCreate(
            name="Production API",
            description="Production data API",
            protocol_type=ProtocolType.HTTP,
            endpoint_config=EndpointConfig(
                target_address="api.prod.com",
                target_port=443,
                endpoint_path="/api/data",
                use_ssl=True,
            ),
            auth_config=AuthConfig(
                auth_type="bearer",
                token="prod-token-123",
            ),
            forwarder_config=ForwarderConfig(
                timeout=60,
                retry_count=5,
            ),
        )

        assert data.name == "Production API"
        assert data.protocol_type == ProtocolType.HTTP
        assert data.endpoint_config.target_address == "api.prod.com"
        assert data.auth_config.auth_type == "bearer"
        assert data.forwarder_config.timeout == 60

    def test_create_without_auth(self):
        """测试创建不需要认证的目标系统"""
        data = TargetSystemCreate(
            name="Public API",
            protocol_type=ProtocolType.UDP,
            endpoint_config=EndpointConfig(
                target_address="udp.example.com",
                target_port=9999,
            ),
        )

        assert data.name == "Public API"
        assert data.auth_config is None
        assert data.forwarder_config is not None  # 有默认值

    def test_create_with_transform_rules(self):
        """测试创建带数据转换规则的目标系统"""
        data = TargetSystemCreate(
            name="Transformed API",
            protocol_type=ProtocolType.HTTP,
            endpoint_config=EndpointConfig(
                target_address="transform.example.com",
                target_port=8080,
            ),
            transform_rules={
                "field_mapping": {
                    "temp": "temperature",
                    "hum": "humidity",
                },
                "add_timestamp": True,
            },
        )

        assert data.transform_rules is not None
        assert "field_mapping" in data.transform_rules

    def test_protocol_normalization(self):
        """测试协议类型自动转换为大写"""
        data = TargetSystemCreate(
            name="Test System",
            protocol_type="http",  # 小写输入
            endpoint_config=EndpointConfig(
                target_address="test.com",
                target_port=80,
            ),
        )

        assert data.protocol_type == ProtocolType.HTTP


class TestTargetSystemUpdate:
    """测试目标系统更新Schema"""

    def test_update_partial_fields(self):
        """测试部分字段更新"""
        data = TargetSystemUpdate(
            name="Updated Name",
            endpoint_config=EndpointConfig(
                target_address="new.address.com",
                target_port=9000,
            ),
        )

        assert data.name == "Updated Name"
        assert data.endpoint_config.target_address == "new.address.com"

    def test_update_auth_config_only(self):
        """测试仅更新认证配置"""
        data = TargetSystemUpdate(
            auth_config=AuthConfig(
                auth_type="api_key",
                api_key="new-api-key",
            ),
        )

        assert data.auth_config.auth_type == "api_key"
        assert data.name is None  # 其他字段未设置


class TestTargetSystemResponse:
    """测试目标系统响应Schema"""

    def test_response_with_all_configs(self):
        """测试响应包含所有配置"""
        ts_id = uuid4()

        response = TargetSystemResponse(
            id=ts_id,
            name="Complete System",
            description="System with all configs",
            protocol_type=ProtocolType.HTTP,
            endpoint_config=EndpointConfig(
                target_address="complete.example.com",
                target_port=443,
                endpoint_path="/api/v1/data",
                use_ssl=True,
            ),
            auth_config=AuthConfig(
                auth_type="bearer",
                token="token123",
            ),
            forwarder_config=ForwarderConfig(
                timeout=45,
                retry_count=4,
                batch_size=50,
            ),
            transform_rules={"mapping": {"a": "b"}},
            is_active=True,
        )

        assert response.id == ts_id
        assert response.endpoint_config.use_ssl is True
        assert response.auth_config.auth_type == "bearer"
        assert response.forwarder_config.batch_size == 50

    def test_response_serialization(self):
        """测试响应序列化"""
        response = TargetSystemResponse(
            id=uuid4(),
            name="Serialization Test",
            protocol_type=ProtocolType.MQTT,
            endpoint_config=EndpointConfig(
                target_address="mqtt.example.com",
                target_port=1883,
            ),
            forwarder_config=ForwarderConfig(),
            is_active=True,
        )

        json_data = response.model_dump_json()

        assert isinstance(json_data, str)
        assert "Serialization Test" in json_data
        assert "MQTT" in json_data


class TestTargetSystemSchemaCompatibility:
    """测试目标系统Schema与前端兼容性"""

    def test_matches_frontend_interface(self):
        """测试匹配前端TargetSystem接口"""
        ts_id = uuid4()

        response = TargetSystemResponse(
            id=ts_id,
            name="Frontend Compatible",
            description="Compatible with frontend",
            protocol_type=ProtocolType.HTTP,
            endpoint_config=EndpointConfig(
                target_address="frontend.example.com",
                target_port=443,
                endpoint_path="/api/data",
                use_ssl=True,
            ),
            auth_config=AuthConfig(
                auth_type="bearer",
                token="frontend-token",
            ),
            forwarder_config=ForwarderConfig(
                timeout=30,
                retry_count=3,
                batch_size=1,
            ),
            transform_rules={"test": "mapping"},
            is_active=True,
        )

        data = response.model_dump()

        # 验证前端期望的字段都存在
        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "protocol_type" in data
        assert "endpoint_config" in data
        assert "auth_config" in data
        assert "transform_rules" in data
        assert "is_active" in data
        assert "created_at" in data
        assert "updated_at" in data

        # 验证嵌套结构
        assert isinstance(data["endpoint_config"], dict)
        assert "target_address" in data["endpoint_config"]
        assert "target_port" in data["endpoint_config"]
        assert isinstance(data["auth_config"], dict)
        assert "auth_type" in data["auth_config"]
