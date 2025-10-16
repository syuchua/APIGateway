"""
HTTP转发器测试用例
采用TDD方法测试HTTP数据转发功能
"""
import base64
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.core.gateway.forwarder.http_forwarder import HTTPForwarder
from app.schemas.forwarder import (
    HTTPForwarderConfig,
    HTTPMethod,
    ForwardResult,
    ForwardStatus
)
from app.schemas.common import ProtocolType


class TestHTTPForwarderConfig:
    """测试HTTP转发器配置"""

    def test_create_basic_config(self):
        """测试创建基本配置"""
        config = HTTPForwarderConfig(
            url="http://localhost:8080/api/data",
            method=HTTPMethod.POST,
            timeout=30
        )

        assert config.url == "http://localhost:8080/api/data"
        assert config.method == HTTPMethod.POST
        assert config.timeout == 30
        assert config.headers == {}
        assert config.retry_times == 3

    def test_config_with_headers(self):
        """测试带请求头的配置"""
        config = HTTPForwarderConfig(
            url="http://api.example.com/data",
            method=HTTPMethod.POST,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token123"
            },
            timeout=60,
            retry_times=5
        )

        assert config.headers["Content-Type"] == "application/json"
        assert config.headers["Authorization"] == "Bearer token123"
        assert config.timeout == 60
        assert config.retry_times == 5

    def test_config_with_auth(self):
        """测试带认证的配置"""
        config = HTTPForwarderConfig(
            url="http://api.example.com/data",
            method=HTTPMethod.POST,
            username="admin",
            password="secret123"
        )

        assert config.username == "admin"
        assert config.password == "secret123"


class TestHTTPForwarder:
    """测试HTTP转发器核心功能"""

    @pytest.fixture
    def forwarder_config(self):
        """创建转发器配置"""
        return HTTPForwarderConfig(
            url="http://localhost:8888/api/data",
            method=HTTPMethod.POST,
            timeout=10,
            retry_times=3
        )

    @pytest.fixture
    async def forwarder(self, forwarder_config):
        """创建HTTP转发器实例"""
        forwarder = HTTPForwarder(forwarder_config)
        yield forwarder
        # 清理
        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forwarder_initialization(self, forwarder, forwarder_config):
        """测试转发器初始化"""
        assert forwarder.config == forwarder_config
        assert forwarder.client is not None

    @pytest.mark.asyncio
    async def test_forward_success(self, forwarder):
        """测试成功转发数据"""
        # Mock HTTP响应
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}
            mock_post.return_value = mock_response

            # 准备测试数据
            data = {
                "message_id": "test-123",
                "temperature": 25.5,
                "humidity": 60.0
            }

            # 转发数据
            result = await forwarder.forward(data)

            # 验证结果
            assert result.status == ForwardStatus.SUCCESS
            assert result.status_code == 200
            assert result.error is None

            # 验证HTTP调用
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_with_json_serialization(self, forwarder):
        """测试JSON序列化"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{}'
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            data = {
                "message_id": "test-456",
                "parsed_data": {
                    "temperature": 30.5,
                    "humidity": 65.0
                },
                "timestamp": "2024-01-01T12:00:00"
            }

            result = await forwarder.forward(data)

            assert result.status == ForwardStatus.SUCCESS

            # 验证发送的是JSON数据
            call_kwargs = mock_post.call_args[1]
            assert 'json' in call_kwargs

    @pytest.mark.asyncio
    async def test_forward_serializes_special_types(self, forwarder):
        """测试字节与时间类型被正确序列化"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{}'
            mock_post.return_value = mock_response

            data = {
                "raw": b"\x01\x02",
                "items": [b"a"],
                "timestamp": datetime(2025, 1, 1, 12, 0, 0)
            }

            await forwarder.forward(data)

            payload = mock_post.call_args[1]["json"]
            assert payload["raw"] == base64.b64encode(b"\x01\x02").decode("ascii")
            assert payload["items"][0] == base64.b64encode(b"a").decode("ascii")
            assert payload["timestamp"] == "2025-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_forward_with_custom_headers(self):
        """测试自定义请求头"""
        config = HTTPForwarderConfig(
            url="http://localhost:8888/api/data",
            method=HTTPMethod.POST,
            headers={
                "X-Custom-Header": "test-value",
                "Authorization": "Bearer token123"
            }
        )

        forwarder = HTTPForwarder(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{}'
            mock_post.return_value = mock_response

            data = {"test": "data"}
            await forwarder.forward(data)

            # 验证请求头
            call_kwargs = mock_post.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert headers["X-Custom-Header"] == "test-value"
            assert headers["Authorization"] == "Bearer token123"

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forward_http_error(self, forwarder):
        """测试HTTP错误处理"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_post.return_value = mock_response

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证错误处理
            assert result.status == ForwardStatus.FAILED
            assert result.status_code == 500
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_forward_timeout(self):
        """测试超时处理"""
        config = HTTPForwarderConfig(
            url="http://localhost:8888/api/data",
            method=HTTPMethod.POST,
            timeout=1  # 1秒超时
        )

        forwarder = HTTPForwarder(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            # 模拟超时
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证超时处理
            assert result.status == ForwardStatus.TIMEOUT
            assert "timeout" in result.error.lower()

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forward_network_error(self, forwarder):
        """测试网络错误处理"""
        with patch('httpx.AsyncClient.post') as mock_post:
            # 模拟网络错误
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证网络错误处理
            assert result.status == ForwardStatus.FAILED
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_forward_with_retry(self):
        """测试重试机制"""
        config = HTTPForwarderConfig(
            url="http://localhost:8888/api/data",
            method=HTTPMethod.POST,
            retry_times=3,
            retry_delay=0.1  # 短延迟便于测试
        )

        forwarder = HTTPForwarder(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            # 前2次失败，第3次成功
            mock_response_fail = Mock()
            mock_response_fail.status_code = 500
            mock_response_fail.text = 'Error'

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.text = '{}'

            mock_post.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证重试后成功
            assert result.status == ForwardStatus.SUCCESS
            assert result.retry_count == 2  # 重试了2次
            assert mock_post.call_count == 3  # 总共调用3次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forward_retry_exhausted(self):
        """测试重试次数用尽"""
        config = HTTPForwarderConfig(
            url="http://localhost:8888/api/data",
            method=HTTPMethod.POST,
            retry_times=2,
            retry_delay=0.1
        )

        forwarder = HTTPForwarder(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            # 所有请求都失败
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Error'
            mock_post.return_value = mock_response

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证重试用尽后失败
            assert result.status == ForwardStatus.FAILED
            assert result.retry_count == 2
            assert mock_post.call_count == 3  # 初始1次 + 重试2次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_batch_forward(self):
        """测试批量转发"""
        config = HTTPForwarderConfig(
            url="http://localhost:8888/api/batch",
            method=HTTPMethod.POST
        )

        forwarder = HTTPForwarder(config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{}'
            mock_post.return_value = mock_response

            # 批量数据
            data_list = [
                {"message_id": f"msg-{i}", "value": i}
                for i in range(10)
            ]

            results = await forwarder.forward_batch(data_list)

            # 验证批量转发结果
            assert len(results) == 10
            assert all(r.status == ForwardStatus.SUCCESS for r in results)

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_different_http_methods(self):
        """测试不同的HTTP方法"""
        for method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
            config = HTTPForwarderConfig(
                url="http://localhost:8888/api/data",
                method=method
            )

            forwarder = HTTPForwarder(config)

            with patch(f'httpx.AsyncClient.{method.value.lower()}') as mock_method:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = '{}'
                mock_method.return_value = mock_response

                data = {"test": "data"}
                result = await forwarder.forward(data)

                assert result.status == ForwardStatus.SUCCESS
                mock_method.assert_called_once()

            await forwarder.close()


class TestHTTPForwarderIntegration:
    """测试HTTP转发器集成"""

    @pytest.mark.skip("外部服务依赖不稳定，跳过真实 HTTP 集成测试")
    @pytest.mark.asyncio
    async def test_forward_with_httpbin(self):
        """测试使用httpbin.org进行真实HTTP请求"""
        # 使用httpbin.org作为测试目标（公共测试API）
        config = HTTPForwarderConfig(
            url="https://httpbin.org/post",
            method=HTTPMethod.POST,
            timeout=30
        )

        forwarder = HTTPForwarder(config)

        test_data = {
            "message_id": "integration-test",
            "temperature": 25.5,
            "humidity": 60.0
        }

        result = await forwarder.forward(test_data)

        # 验证转发成功
        assert result.status == ForwardStatus.SUCCESS
        assert result.status_code == 200

        await forwarder.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
