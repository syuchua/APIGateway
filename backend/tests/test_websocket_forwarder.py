"""
WebSocket转发器测试用例
采用TDD方法测试WebSocket数据转发功能
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import websockets

from app.core.gateway.forwarder.websocket_forwarder import WebSocketForwarder
from app.schemas.forwarder import (
    WebSocketForwarderConfig,
    ForwardResult,
    ForwardStatus
)
from app.schemas.common import ProtocolType


class TestWebSocketForwarderConfig:
    """测试WebSocket转发器配置"""

    def test_create_basic_config(self):
        """测试创建基本配置"""
        config = WebSocketForwarderConfig(
            url="ws://localhost:8080/ws",
            timeout=30
        )

        assert config.url == "ws://localhost:8080/ws"
        assert config.timeout == 30
        assert config.headers == {}
        assert config.retry_times == 3
        assert config.ping_interval == 30

    def test_config_with_headers(self):
        """测试带请求头的配置"""
        config = WebSocketForwarderConfig(
            url="wss://api.example.com/ws",
            headers={
                "Authorization": "Bearer token123",
                "X-Client-ID": "gateway-client"
            },
            timeout=60,
            retry_times=5
        )

        assert config.headers["Authorization"] == "Bearer token123"
        assert config.headers["X-Client-ID"] == "gateway-client"
        assert config.timeout == 60
        assert config.retry_times == 5

    def test_config_with_wss_url(self):
        """测试WebSocket安全连接配置"""
        config = WebSocketForwarderConfig(
            url="wss://secure.example.com/ws",
            ping_interval=60,
            ping_timeout=20
        )

        assert config.url.startswith("wss://")
        assert config.ping_interval == 60
        assert config.ping_timeout == 20


class TestWebSocketForwarder:
    """测试WebSocket转发器核心功能"""

    @pytest.fixture
    def forwarder_config(self):
        """创建转发器配置"""
        return WebSocketForwarderConfig(
            url="ws://localhost:8080/ws",
            timeout=10,
            retry_times=3,
            ping_interval=30
        )

    @pytest.fixture
    async def forwarder(self, forwarder_config):
        """创建WebSocket转发器实例"""
        forwarder = WebSocketForwarder(forwarder_config)
        yield forwarder
        # 清理
        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forwarder_initialization(self, forwarder, forwarder_config):
        """测试转发器初始化"""
        assert forwarder.config == forwarder_config
        assert forwarder.connection is None
        assert forwarder.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self, forwarder):
        """测试成功连接WebSocket"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            # 连接WebSocket
            await forwarder._connect()

            # 验证连接
            assert forwarder.is_connected is True
            assert forwarder.connection == mock_ws
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, forwarder):
        """测试连接失败"""
        with patch('websockets.connect') as mock_connect:
            # Mock连接失败
            mock_connect.side_effect = Exception("Connection failed")

            # 尝试连接
            await forwarder._connect()

            # 验证连接失败
            assert forwarder.is_connected is False
            assert forwarder.connection is None

    @pytest.mark.asyncio
    async def test_forward_success(self, forwarder):
        """测试成功转发数据"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

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
            assert result.error is None
            assert result.retry_count == 0

            # 验证WebSocket发送
            mock_ws.send.assert_called_once()
            # 验证发送的是JSON字符串
            sent_data = json.loads(mock_ws.send.call_args[0][0])
            assert sent_data == data

    @pytest.mark.asyncio
    async def test_forward_with_connection_reuse(self, forwarder):
        """测试连接复用"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            # 发送多条消息
            data1 = {"message_id": "msg-1", "value": 1}
            data2 = {"message_id": "msg-2", "value": 2}

            result1 = await forwarder.forward(data1)
            result2 = await forwarder.forward(data2)

            # 验证结果
            assert result1.status == ForwardStatus.SUCCESS
            assert result2.status == ForwardStatus.SUCCESS

            # 验证只建立了一次连接
            assert mock_connect.call_count == 1
            assert mock_ws.send.call_count == 2

    @pytest.mark.asyncio
    async def test_forward_connection_error(self, forwarder):
        """测试连接错误处理"""
        with patch('websockets.connect') as mock_connect:
            # Mock连接失败
            mock_connect.side_effect = Exception("Connection refused")

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证错误处理
            assert result.status == ForwardStatus.FAILED
            # 错误消息可能是"Connection refused"或"Failed to establish WebSocket connection"
            assert "Connection refused" in result.error or "Failed to establish WebSocket connection" in result.error

    @pytest.mark.asyncio
    async def test_forward_send_error(self, forwarder):
        """测试发送错误处理"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send.side_effect = Exception("Send failed")
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证错误处理
            assert result.status == ForwardStatus.FAILED
            assert "Send failed" in result.error

    @pytest.mark.asyncio
    async def test_forward_with_retry(self):
        """测试重试机制"""
        config = WebSocketForwarderConfig(
            url="ws://localhost:8080/ws",
            retry_times=3,
            retry_delay=0.1  # 短延迟便于测试
        )

        forwarder = WebSocketForwarder(config)

        with patch('websockets.connect') as mock_connect:
            call_count = 0
            
            def mock_connect_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # 前两次失败
                    raise Exception("Connection failed")
                
                # 第三次成功
                mock_ws = AsyncMock()
                mock_ws.send = AsyncMock()
                mock_ws.close = AsyncMock()
                mock_ws.ping = AsyncMock()
                return mock_ws

            mock_connect.side_effect = mock_connect_side_effect

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证重试后成功
            assert result.status == ForwardStatus.SUCCESS
            assert result.retry_count == 2  # 重试了2次
            assert mock_connect.call_count == 3  # 总共尝试3次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forward_retry_exhausted(self):
        """测试重试次数用尽"""
        config = WebSocketForwarderConfig(
            url="ws://localhost:8080/ws",
            retry_times=2,
            retry_delay=0.1
        )

        forwarder = WebSocketForwarder(config)

        with patch('websockets.connect') as mock_connect:
            # 所有连接都失败
            mock_connect.side_effect = Exception("Connection failed")

            data = {"test": "data"}
            result = await forwarder.forward(data)

            # 验证重试用尽后失败
            assert result.status == ForwardStatus.FAILED
            assert result.retry_count == 2
            assert mock_connect.call_count == 3  # 初始1次 + 重试2次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_batch_forward(self, forwarder):
        """测试批量转发"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            # 批量数据
            data_list = [
                {"message_id": f"msg-{i}", "value": i}
                for i in range(5)
            ]

            results = await forwarder.forward_batch(data_list)

            # 验证批量转发结果
            assert len(results) == 5
            assert all(r.status == ForwardStatus.SUCCESS for r in results)

            # 验证WebSocket发送次数
            assert mock_ws.send.call_count == 5

    @pytest.mark.asyncio
    async def test_close_connection(self, forwarder):
        """测试关闭连接"""
        with patch('websockets.connect') as mock_connect:
            # Mock WebSocket连接
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            # 建立连接
            await forwarder._connect()
            assert forwarder.is_connected is True

            # 关闭连接
            await forwarder.close()

            # 验证连接已关闭
            assert forwarder.is_connected is False
            assert forwarder.connection is None
            mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_with_custom_headers(self):
        """测试自定义请求头"""
        config = WebSocketForwarderConfig(
            url="ws://localhost:8080/ws",
            headers={
                "Authorization": "Bearer token123",
                "X-Client-ID": "gateway-client"
            }
        )

        forwarder = WebSocketForwarder(config)

        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            data = {"test": "data"}
            await forwarder.forward(data)

            # 验证请求头传递
            call_kwargs = mock_connect.call_args[1]
            assert 'extra_headers' in call_kwargs
            headers = call_kwargs['extra_headers']
            assert headers["Authorization"] == "Bearer token123"
            assert headers["X-Client-ID"] == "gateway-client"

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_get_stats(self, forwarder):
        """测试获取统计信息"""
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.ping = AsyncMock()
            mock_connect.return_value = mock_ws

            # 发送一些数据
            data = {"test": "data"}
            await forwarder.forward(data)

            # 获取统计信息
            stats = forwarder.get_stats()

            # 验证统计信息
            assert stats["forwards_attempted"] == 1
            assert stats["forwards_succeeded"] == 1
            assert stats["forwards_failed"] == 0
            assert stats["success_rate"] == 1.0


class TestWebSocketForwarderIntegration:
    """测试WebSocket转发器集成"""

    @pytest.mark.asyncio
    async def test_forward_to_echo_server(self):
        """测试使用WebSocket echo服务器进行真实测试"""
        # 注意：这个测试需要有一个WebSocket echo服务器运行
        # 这里我们使用公共的WebSocket测试服务器
        config = WebSocketForwarderConfig(
            url="wss://ws.postman-echo.com/raw",
            timeout=30
        )

        forwarder = WebSocketForwarder(config)

        test_data = {
            "message_id": "integration-test",
            "temperature": 25.5,
            "humidity": 60.0
        }

        result = await forwarder.forward(test_data)

        # 验证转发成功（即使没有响应，只要发送成功就算成功）
        assert result.status == ForwardStatus.SUCCESS

        await forwarder.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])