"""
前后端接口兼容性集成测试
"""
import pytest
from uuid import uuid4
import base64

# 测试新的Schema导入
from app.schemas.data_source_v2 import DataSourceCreate, DataSourceResponse, ConnectionConfig, ParseConfig
from app.schemas.target_system_v2 import TargetSystemCreate, TargetSystemResponse, EndpointConfig, AuthConfig, ForwarderConfig
from app.schemas.response import ApiResponse, PaginatedResponse, success_response, error_response, paginated_response
from app.schemas.message_v2 import UnifiedMessage, UnifiedMessageResponse
from app.schemas.routing_rule_simple import RoutingRuleSimpleResponse
from app.schemas.websocket import (
    WebSocketMessage,
    MonitorMessage,
    MonitorData,
    create_monitor_message,
    create_log_message
)
from app.schemas.common import ProtocolType


class TestProtocolTypeCompatibility:
    """测试协议类型兼容性"""

    def test_websocket_protocol_uppercase(self):
        """测试WEBSOCKET枚举值为全大写"""
        assert ProtocolType.WEBSOCKET == "WEBSOCKET"
        assert ProtocolType.WEBSOCKET.value == "WEBSOCKET"

    def test_all_protocols_uppercase(self):
        """测试所有协议类型都是大写"""
        for protocol in ProtocolType:
            assert protocol.value == protocol.value.upper()


class TestDataSourceSchemaCompatibility:
    """测试数据源Schema与前端兼容性"""

    def test_create_data_source_nested_config(self):
        """测试创建数据源使用嵌套配置"""
        data = DataSourceCreate(
            name="Test Source",
            description="Test",
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
        )

        # 转换为字典（前端JSON格式）
        data_dict = data.model_dump()

        # 验证结构匹配前端期望
        assert "name" in data_dict
        assert "protocol_type" in data_dict
        assert "connection_config" in data_dict
        assert "parse_config" in data_dict

        # 验证嵌套结构
        assert isinstance(data_dict["connection_config"], dict)
        assert "listen_address" in data_dict["connection_config"]
        assert "listen_port" in data_dict["connection_config"]

    def test_data_source_response_structure(self):
        """测试数据源响应结构"""
        response = DataSourceResponse(
            id=uuid4(),
            name="Test Source",
            description="Test",
            protocol_type=ProtocolType.HTTP,
            connection_config=ConnectionConfig(listen_port=8080),
            parse_config=ParseConfig(auto_parse=True),
            is_active=True,
        )

        data = response.model_dump()

        # 验证必需字段
        required_fields = [
            "id", "name", "protocol_type",
            "connection_config", "parse_config",
            "is_active", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in data


class TestTargetSystemSchemaCompatibility:
    """测试目标系统Schema与前端兼容性"""

    def test_create_target_system_with_auth(self):
        """测试创建带认证的目标系统"""
        data = TargetSystemCreate(
            name="Secure API",
            protocol_type=ProtocolType.HTTP,
            endpoint_config=EndpointConfig(
                target_address="api.example.com",
                target_port=443,
                endpoint_path="/api/data",
                use_ssl=True,
            ),
            auth_config=AuthConfig(
                auth_type="bearer",
                token="secret-token-123",
            ),
            forwarder_config=ForwarderConfig(
                timeout=60,
                retry_count=5,
            ),
        )

        data_dict = data.model_dump()

        # 验证结构
        assert "endpoint_config" in data_dict
        assert "auth_config" in data_dict
        assert "forwarder_config" in data_dict

        # 验证auth_config存在且正确
        assert data_dict["auth_config"]["auth_type"] == "bearer"
        assert data_dict["auth_config"]["token"] == "secret-token-123"

    def test_target_system_response_structure(self):
        """测试目标系统响应结构"""
        response = TargetSystemResponse(
            id=uuid4(),
            name="Test System",
            protocol_type=ProtocolType.MQTT,
            endpoint_config=EndpointConfig(
                target_address="mqtt.example.com",
                target_port=1883,
            ),
            forwarder_config=ForwarderConfig(),
            is_active=True,
        )

        data = response.model_dump()

        # 验证必需字段
        required_fields = [
            "id", "name", "protocol_type",
            "endpoint_config", "forwarder_config",
            "is_active", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in data


class TestApiResponseCompatibility:
    """测试API响应格式兼容性"""

    def test_success_response_format(self):
        """测试成功响应格式"""
        response = success_response(
            data={"id": "123", "name": "Test"},
            message="操作成功"
        )

        assert response["success"] is True
        assert "data" in response
        assert "message" in response
        assert response["code"] == 200

    def test_error_response_format(self):
        """测试错误响应格式"""
        response = error_response(
            error="资源不存在",
            detail="数据源ID不存在",
            code=404
        )

        assert response["success"] is False
        assert "error" in response
        assert "detail" in response
        assert response["code"] == 404

    def test_paginated_response_format(self):
        """测试分页响应格式"""
        items = [{"id": i, "name": f"Item {i}"} for i in range(10)]
        response = paginated_response(
            items=items,
            page=1,
            limit=10,
            total=100
        )

        assert response["success"] is True
        assert "items" in response
        assert "pagination" in response
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["limit"] == 10
        assert response["pagination"]["total"] == 100
        assert response["pagination"]["total_pages"] == 10


class TestUnifiedMessageCompatibility:
    """测试统一消息格式兼容性"""

    def test_unified_message_all_fields(self):
        """测试统一消息包含所有字段"""
        msg = UnifiedMessage(
            message_id="msg-123",
            trace_id="trace-456",
            source_protocol=ProtocolType.UDP,
            source_id="source-001",
            source_address="192.168.1.100",
            source_port=9999,
            raw_data=b"test data",
            data_size=9,
            parsed_data={"temp": 25.5},
            frame_schema_id="frame-001",
            processing_status="PROCESSED",
            target_systems=["sys-001", "sys-002"],
            routing_rules=["rule-001"],
            error_code=None,
            processing_duration_ms=10,
        )

        # 验证所有字段存在
        assert msg.message_id == "msg-123"
        assert msg.trace_id == "trace-456"
        assert msg.source_address == "192.168.1.100"
        assert msg.source_port == 9999
        assert msg.data_size == 9
        assert msg.frame_schema_id == "frame-001"
        assert msg.error_code is None
        assert msg.processing_duration_ms == 10

    def test_unified_message_response_base64(self):
        """测试统一消息响应raw_data为base64编码"""
        # 模拟将UnifiedMessage转换为Response
        raw_data = b"binary data"
        raw_data_base64 = base64.b64encode(raw_data).decode('utf-8')

        response = UnifiedMessageResponse(
            message_id="msg-123",
            timestamp="2025-10-13T10:00:00Z",
            trace_id="trace-456",
            source_protocol=ProtocolType.TCP,
            source_id="source-001",
            raw_data=raw_data_base64,  # base64编码
            data_size=len(raw_data),
            processing_status="PENDING",
            target_systems=[],
            routing_rules=[],
        )

        assert response.raw_data == raw_data_base64
        assert isinstance(response.raw_data, str)


class TestRoutingRuleSimpleResponse:
    """测试简化路由规则响应"""

    def test_simple_response_structure(self):
        """测试简化响应结构"""
        response = RoutingRuleSimpleResponse(
            id=uuid4(),
            name="Simple Rule",
            description="Test",
            priority=50,
            source_pattern="sensor.*",
            target_system_ids=["sys-001", "sys-002"],
            is_active=True,
            is_published=True,
            match_count=100,
        )

        data = response.model_dump()

        # 验证简化字段
        assert "target_system_ids" in data
        assert isinstance(data["target_system_ids"], list)
        assert "source_pattern" in data
        assert "match_count" in data


class TestWebSocketMessageCompatibility:
    """测试WebSocket消息格式兼容性"""

    def test_monitor_message_format(self):
        """测试监控消息格式"""
        monitor_data = MonitorData(
            gateway_status="running",
            adapters_running=5,
            adapters_total=10,
            forwarders_active=3,
            messages_per_second=1000.5,
            messages_total=1000000,
            error_rate=0.01,
            cpu_usage=45.5,
            memory_usage=60.2,
        )

        message = create_monitor_message(monitor_data)

        assert message["type"] == "monitor"
        assert "timestamp" in message
        assert "data" in message
        assert message["data"]["gateway_status"] == "running"
        assert message["data"]["messages_per_second"] == 1000.5

    def test_log_message_format(self):
        """测试日志消息格式"""
        message = create_log_message(
            level="INFO",
            message="Test log message",
            source="test_source",
            extra={"key": "value"}
        )

        assert message["type"] == "log"
        assert "timestamp" in message
        assert message["data"]["level"] == "INFO"
        assert message["data"]["message"] == "Test log message"

    def test_websocket_message_types(self):
        """测试WebSocket消息类型定义"""
        # 验证所有消息类型都有正确的type字段
        monitor_msg = MonitorMessage(data=MonitorData(
            gateway_status="running",
            adapters_running=0,
            adapters_total=0,
            forwarders_active=0,
            messages_per_second=0,
            messages_total=0,
            error_rate=0,
        ))

        assert monitor_msg.type == "monitor"


class TestFrontendBackendIntegration:
    """测试前后端完整集成场景"""

    def test_complete_data_source_flow(self):
        """测试数据源完整流程"""
        # 1. 创建请求（前端发送）
        create_dto = DataSourceCreate(
            name="Integration Test Source",
            protocol_type="udp",  # 测试自动转换
            connection_config=ConnectionConfig(
                listen_port=9999,
                max_connections=100,
            ),
            parse_config=ParseConfig(auto_parse=True),
        )

        # 2. 验证协议类型转换
        assert create_dto.protocol_type == ProtocolType.UDP

        # 3. 模拟响应（后端返回）
        response = DataSourceResponse(
            id=uuid4(),
            name=create_dto.name,
            protocol_type=create_dto.protocol_type,
            connection_config=create_dto.connection_config,
            parse_config=create_dto.parse_config,
            is_active=True,
        )

        # 4. 验证前端可以正确解析
        response_dict = response.model_dump()
        assert response_dict["protocol_type"] == "UDP"
        assert response_dict["connection_config"]["listen_port"] == 9999

    def test_complete_api_response_flow(self):
        """测试API响应完整流程"""
        # 1. 创建数据
        data_source = {
            "id": str(uuid4()),
            "name": "Test",
            "protocol_type": "HTTP",
        }

        # 2. 包装为API响应
        api_response = success_response(
            data=data_source,
            message="创建成功"
        )

        # 3. 验证前端期望的结构
        assert api_response["success"] is True
        assert api_response["data"]["name"] == "Test"
        assert api_response["message"] == "创建成功"
