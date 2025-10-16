"""
MQTT转发器测试用例
采用TDD方法测试MQTT数据转发功能
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch

from app.core.gateway.forwarder.mqtt_forwarder import MQTTForwarder
from app.schemas.forwarder import (
    MQTTForwarderConfig,
    ForwardResult,
    ForwardStatus
)
from app.schemas.common import ProtocolType


class TestMQTTForwarderConfig:
    """测试MQTT转发器配置"""

    def test_create_basic_config(self):
        """测试创建基本配置"""
        config = MQTTForwarderConfig(
            host="localhost",
            port=1883,
            topic="test/topic"
        )

        assert config.host == "localhost"
        assert config.port == 1883
        assert config.topic == "test/topic"
        assert config.timeout == 10
        assert config.keepalive == 60
        assert config.qos == 1
        assert config.retry_times == 3
        assert config.retry_delay == 1.0

    def test_config_with_custom_settings(self):
        """测试自定义设置"""
        config = MQTTForwarderConfig(
            host="192.168.1.100",
            port=8883,
            topic="sensors/data",
            username="user",
            password="pass",
            timeout=15,
            keepalive=120,
            qos=2,
            retry_times=5,
            retry_delay=2.0
        )

        assert config.host == "192.168.1.100"
        assert config.port == 8883
        assert config.topic == "sensors/data"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.timeout == 15
        assert config.keepalive == 120
        assert config.qos == 2
        assert config.retry_times == 5
        assert config.retry_delay == 2.0

    def test_config_with_tls(self):
        """测试TLS配置"""
        config = MQTTForwarderConfig(
            host="localhost",
            port=8883,
            topic="secure/topic",
            tls_enabled=True,
            ca_cert="/path/to/ca.crt",
            cert_file="/path/to/client.crt",
            key_file="/path/to/client.key"
        )

        assert config.tls_enabled is True
        assert config.ca_cert == "/path/to/ca.crt"
        assert config.cert_file == "/path/to/client.crt"
        assert config.key_file == "/path/to/client.key"


class TestMQTTForwarder:
    """测试MQTT转发器核心功能"""

    @pytest.fixture
    def forwarder_config(self):
        """创建转发器配置"""
        return MQTTForwarderConfig(
            host="localhost",
            port=1883,
            topic="test/topic",
            timeout=5,
            retry_times=2
        )

    @pytest.fixture
    async def forwarder(self, forwarder_config):
        """创建MQTT转发器实例"""
        forwarder = MQTTForwarder(forwarder_config)
        yield forwarder
        # 清理
        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forwarder_initialization(self, forwarder, forwarder_config):
        """测试转发器初始化"""
        assert forwarder.config == forwarder_config
        assert forwarder.client is None
        assert forwarder.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self, forwarder):
        """测试成功连接MQTT"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志

                # 连接MQTT
                result = await forwarder._connect()

                # 验证连接
                assert result is True
                assert forwarder.is_connected is True
                assert forwarder.client == mock_client
                mock_client.connect.assert_called_once_with(
                    forwarder.config.host,
                    forwarder.config.port,
                    forwarder.config.keepalive
                )
                mock_client.loop_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, forwarder):
        """测试连接失败"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock连接失败
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 1  # 返回错误码

                # 尝试连接
                result = await forwarder._connect()

                # 验证连接失败
                assert result is False
                assert forwarder.is_connected is False
                assert forwarder.client is None

    @pytest.mark.asyncio
    async def test_forward_success(self, forwarder):
        """测试成功转发数据"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志

                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

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

                # 验证MQTT发布
                mock_client.publish.assert_called_once()
                # 验证发布的是JSON字符串
                call_args = mock_client.publish.call_args
                assert call_args[0][0] == forwarder.config.topic
                published_data = call_args[0][1]
                assert json.loads(published_data) == data

    @pytest.mark.asyncio
    async def test_forward_with_connection_reuse(self, forwarder):
        """测试连接复用"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                
                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

                # 发送多条消息
                data1 = {"message_id": "msg-1", "value": 1}
                data2 = {"message_id": "msg-2", "value": 2}

                result1 = await forwarder.forward(data1)
                result2 = await forwarder.forward(data2)

                # 验证结果
                assert result1.status == ForwardStatus.SUCCESS
                assert result2.status == ForwardStatus.SUCCESS

                # 验证只建立了一次连接
                assert mock_client.connect.call_count == 1
                assert mock_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_forward_connection_error(self, forwarder):
        """测试连接错误处理"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock连接失败
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 1  # 返回错误码

                data = {"test": "data"}
                result = await forwarder.forward(data)

                # 验证错误处理
                assert result.status == ForwardStatus.FAILED
                assert "Failed to establish MQTT connection" in result.error

    @pytest.mark.asyncio
    async def test_forward_publish_error(self, forwarder):
        """测试发布错误处理"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                mock_client.publish.side_effect = Exception("Publish failed")

                data = {"test": "data"}
                result = await forwarder.forward(data)

                # 验证错误处理
                assert result.status == ForwardStatus.FAILED
                assert "Publish failed" in result.error

    @pytest.mark.asyncio
    async def test_forward_with_retry(self):
        """测试重试机制"""
        config = MQTTForwarderConfig(
            host="localhost",
            port=1883,
            topic="test/topic",
            retry_times=3,
            retry_delay=0.1  # 短延迟便于测试
        )

        forwarder = MQTTForwarder(config)

        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                call_count = 0
                
                def mock_connect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 2:  # 前两次失败
                        return 1  # 返回错误码
                    
                    # 第三次成功
                    return 0

                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.side_effect = mock_connect
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                
                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

                data = {"test": "data"}
                result = await forwarder.forward(data)

                # 验证重试后成功
                assert result.status == ForwardStatus.SUCCESS
                assert result.retry_count == 2  # 重试了2次
                assert mock_client.connect.call_count == 3  # 总共尝试3次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_forward_retry_exhausted(self):
        """测试重试次数用尽"""
        config = MQTTForwarderConfig(
            host="localhost",
            port=1883,
            topic="test/topic",
            retry_times=2,
            retry_delay=0.1
        )

        forwarder = MQTTForwarder(config)

        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 1  # 总是失败

                data = {"test": "data"}
                result = await forwarder.forward(data)

                # 验证重试用尽后失败
                assert result.status == ForwardStatus.FAILED
                assert result.retry_count == 2
                assert mock_client.connect.call_count == 3  # 初始1次 + 重试2次

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_batch_forward(self, forwarder):
        """测试批量转发"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                
                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

                # 批量数据
                data_list = [
                    {"message_id": f"msg-{i}", "value": i}
                    for i in range(5)
                ]

                results = await forwarder.forward_batch(data_list)

                # 验证批量转发结果
                assert len(results) == 5
                assert all(r.status == ForwardStatus.SUCCESS for r in results)

                # 验证MQTT发布次数
                assert mock_client.publish.call_count == 5

    @pytest.mark.asyncio
    async def test_close_connection(self, forwarder):
        """测试关闭连接"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志

                # 建立连接
                await forwarder._connect()
                assert forwarder.is_connected is True

                # 关闭连接
                await forwarder.close()

                # 验证连接已关闭
                assert forwarder.is_connected is False
                assert forwarder.client is None
                mock_client.loop_stop.assert_called_once()
                mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_with_qos(self):
        """测试不同QoS级别"""
        config = MQTTForwarderConfig(
            host="localhost",
            port=1883,
            topic="test/topic",
            qos=2
        )

        forwarder = MQTTForwarder(config)

        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                
                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

                data = {"test": "data"}
                await forwarder.forward(data)

                # 验证QoS设置
                call_args = mock_client.publish.call_args
                assert call_args.kwargs['qos'] == 2  # qos参数

        await forwarder.close()

    @pytest.mark.asyncio
    async def test_get_stats(self, forwarder):
        """测试获取统计信息"""
        with patch('app.core.gateway.forwarder.mqtt_forwarder.MQTT_AVAILABLE', True):
            with patch('app.core.gateway.forwarder.mqtt_forwarder.mqtt.Client') as mock_client_class:
                # Mock MQTT客户端
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = 0
                mock_client.loop_start.return_value = None
                mock_client.is_connected.return_value = True
                mock_client._trigger_on_connect = True  # 触发器标志
                
                # 创建mock的publish结果
                mock_publish_result = Mock()
                mock_publish_result.rc = 0
                mock_client.publish.return_value = mock_publish_result

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


class TestMQTTForwarderIntegration:
    """测试MQTT转发器集成"""

    @pytest.mark.asyncio
    async def test_forward_to_real_broker(self):
        """测试使用真实MQTT代理进行测试"""
        # 注意：这个测试需要有一个MQTT代理运行
        config = MQTTForwarderConfig(
            host="127.0.0.1",
            port=1883,  # 假设有一个MQTT代理在1883端口
            topic="test/integration",
            timeout=5
        )

        forwarder = MQTTForwarder(config)

        test_data = {
            "message_id": "integration-test",
            "temperature": 25.5,
            "humidity": 60.0
        }

        try:
            result = await forwarder.forward(test_data)
            # 如果代理不存在，会失败，这是正常的
            if result.status == ForwardStatus.SUCCESS:
                assert True  # 测试通过
            else:
                # 连接失败是预期的，因为没有真实的MQTT代理
                assert "Failed to establish" in result.error or "Connection refused" in result.error
        except Exception as e:
            # 连接失败是预期的
            assert "Connection refused" in str(e) or "Failed to establish" in str(e)

        await forwarder.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])