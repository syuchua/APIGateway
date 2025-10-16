"""
EventBus核心功能测试用例
采用TDD方法，先编写测试用例，后实现功能
"""
import pytest
import asyncio
import threading
import time
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from app.core.eventbus.eventbus import SimpleEventBus, EventSubscriber


class TestSimpleEventBus:
    """SimpleEventBus核心测试"""

    @pytest.fixture
    def eventbus(self):
        """创建EventBus实例"""
        return SimpleEventBus()

    def test_eventbus_initialization(self, eventbus):
        """测试EventBus初始化"""
        assert eventbus is not None
        assert len(eventbus._subscribers) == 0

    def test_subscribe_single_callback(self, eventbus):
        """测试订阅单个回调"""
        callback = Mock()

        subscriber_id = eventbus.subscribe("TEST_TOPIC", callback)

        assert subscriber_id is not None
        assert len(eventbus._subscribers["TEST_TOPIC"]) == 1

    def test_subscribe_multiple_callbacks(self, eventbus):
        """测试订阅多个回调"""
        callback1 = Mock()
        callback2 = Mock()

        id1 = eventbus.subscribe("TEST_TOPIC", callback1)
        id2 = eventbus.subscribe("TEST_TOPIC", callback2)

        assert id1 != id2
        assert len(eventbus._subscribers["TEST_TOPIC"]) == 2

    def test_unsubscribe_callback(self, eventbus):
        """测试取消订阅"""
        callback = Mock()
        subscriber_id = eventbus.subscribe("TEST_TOPIC", callback)

        result = eventbus.unsubscribe(subscriber_id)

        assert result is True
        assert len(eventbus._subscribers["TEST_TOPIC"]) == 0

    def test_unsubscribe_nonexistent_id(self, eventbus):
        """测试取消订阅不存在的ID"""
        result = eventbus.unsubscribe("nonexistent-id")
        assert result is False

    def test_publish_simple_message(self, eventbus):
        """测试发布简单消息"""
        callback = Mock()
        eventbus.subscribe("TEST_TOPIC", callback)

        result = eventbus.publish("test_topic", {"message": "hello"})

        assert result == 1
        callback.assert_called_once_with({"message": "hello"}, "TEST_TOPIC", None)

    def test_publish_with_source(self, eventbus):
        """测试带来源的消息发布"""
        callback = Mock()
        eventbus.subscribe("TEST_TOPIC", callback)

        result = eventbus.publish("test_topic", {"data": 123}, source="test_source")

        assert result == 1
        callback.assert_called_once_with({"data": 123}, "TEST_TOPIC", "test_source")

    def test_publish_to_nonexistent_topic(self, eventbus):
        """测试发布到不存在的主题"""
        result = eventbus.publish("NONEXISTENT_TOPIC", {"data": "test"})
        assert result == 0

    def test_publish_to_multiple_subscribers(self, eventbus):
        """测试发布到多个订阅者"""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        eventbus.subscribe("TEST_TOPIC", callback1)
        eventbus.subscribe("TEST_TOPIC", callback2)
        eventbus.subscribe("OTHER_TOPIC", callback3)

        result = eventbus.publish("test_topic", {"data": "broadcast"})

        assert result == 2
        callback1.assert_called_once_with({"data": "broadcast"}, "TEST_TOPIC", None)
        callback2.assert_called_once_with({"data": "broadcast"}, "TEST_TOPIC", None)
        callback3.assert_not_called()

    def test_wildcard_subscription(self, eventbus):
        """测试通配符订阅"""
        callback = Mock()
        eventbus.subscribe("TEST_*", callback)

        result1 = eventbus.publish("test_message", {"data": 1})
        result2 = eventbus.publish("test_event", {"data": 2})
        result3 = eventbus.publish("other_message", {"data": 3})

        assert result1 == 1
        assert result2 == 1
        assert result3 == 0
        assert callback.call_count == 2

    def test_callback_exception_handling(self, eventbus):
        """测试回调函数异常处理"""
        def failing_callback(data, topic, source):
            raise ValueError("Test exception")

        normal_callback = Mock()

        eventbus.subscribe("TEST_TOPIC", failing_callback)
        eventbus.subscribe("TEST_TOPIC", normal_callback)

        # 应该继续执行其他回调，即使某个回调失败
        result = eventbus.publish("test_topic", {"data": "test"})

        assert result == 2  # 两个回调都被调用
        normal_callback.assert_called_once()

    def test_thread_safety_concurrent_subscribe(self, eventbus):
        """测试并发订阅的线程安全性"""
        callbacks = []
        threads = []

        def subscribe_callback():
            callback = Mock()
            callbacks.append(callback)
            eventbus.subscribe("CONCURRENT_TOPIC", callback)

        # 创建10个并发订阅线程
        for _ in range(10):
            thread = threading.Thread(target=subscribe_callback)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        assert len(eventbus._subscribers["CONCURRENT_TOPIC"]) == 10
        assert len(callbacks) == 10

    def test_thread_safety_concurrent_publish(self, eventbus):
        """测试并发发布的线程安全性"""
        callback = Mock()
        eventbus.subscribe("CONCURRENT_TOPIC", callback)

        results = []
        threads = []

        def publish_message(index):
            result = eventbus.publish("concurrent_topic", {"index": index})
            results.append(result)

        # 创建20个并发发布线程
        for i in range(20):
            thread = threading.Thread(target=publish_message, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        assert len(results) == 20
        assert all(result == 1 for result in results)
        assert callback.call_count == 20

    def test_performance_high_frequency_publish(self, eventbus):
        """测试高频发布性能"""
        callback = Mock()
        eventbus.subscribe("PERF_TOPIC", callback)

        start_time = time.time()

        # 发布10000条消息
        for i in range(10000):
            eventbus.publish("perf_topic", {"index": i})

        duration = time.time() - start_time

        assert callback.call_count == 10000
        assert duration < 1.0  # 应该在1秒内完成

        # 计算吞吐量
        throughput = 10000 / duration
        print(f"EventBus吞吐量: {throughput:.0f} msg/s")
        assert throughput > 30000  # 至少3万msg/s（更现实的目标）

    def test_memory_usage_large_payloads(self, eventbus):
        """测试大负载内存使用"""
        callback = Mock()
        eventbus.subscribe("MEMORY_TOPIC", callback)

        # 发布大数据包
        large_data = {"data": "x" * 10000}  # 10KB数据

        for _ in range(100):
            eventbus.publish("memory_topic", large_data)

        assert callback.call_count == 100


class TestEventSubscriber:
    """EventSubscriber装饰器测试"""

    @pytest.fixture
    def eventbus(self):
        return SimpleEventBus()

    def test_subscriber_decorator(self, eventbus):
        """测试@EventSubscriber装饰器"""

        class TestHandler:
            def __init__(self):
                self.received_messages = []

            @EventSubscriber("TEST_DECORATED")
            def handle_message(self, data, topic, source):
                self.received_messages.append((data, topic, source))

        handler = TestHandler()

        # 注册处理器到EventBus（需要传递实例）
        handler.handle_message.register(eventbus, handler)

        # 发布消息
        eventbus.publish("test_decorated", {"msg": "hello"})

        assert len(handler.received_messages) == 1
        assert handler.received_messages[0] == ({"msg": "hello"}, "TEST_DECORATED", None)


class TestEventBusIntegration:
    """EventBus集成测试"""

    @pytest.fixture
    def eventbus(self):
        return SimpleEventBus()

    def test_data_pipeline_simulation(self, eventbus):
        """模拟数据处理管道"""
        pipeline_results = []

        def udp_adapter(data, topic, source):
            # 模拟UDP适配器接收数据
            processed_data = {"original": data, "protocol": "UDP", "timestamp": time.time()}
            eventbus.publish("DATA_RECEIVED", processed_data, source="udp_adapter")

        def data_processor(data, topic, source):
            # 模拟数据处理器
            if topic == "DATA_RECEIVED":
                processed = {"processed": True, "source_data": data}
                eventbus.publish("DATA_PROCESSED", processed, source="data_processor")

        def data_forwarder(data, topic, source):
            # 模拟数据转发器
            if topic == "DATA_PROCESSED":
                pipeline_results.append(data)

        # 订阅管道
        eventbus.subscribe("UDP_MESSAGE", udp_adapter)
        eventbus.subscribe("DATA_RECEIVED", data_processor)
        eventbus.subscribe("DATA_PROCESSED", data_forwarder)

        # 模拟UDP消息到达
        eventbus.publish("udp_message", {"sensor_id": "temp_01", "value": 25.5})

        # 验证管道处理结果
        assert len(pipeline_results) == 1
        result = pipeline_results[0]
        assert result["processed"] is True
        assert result["source_data"]["original"]["sensor_id"] == "temp_01"

    def test_error_propagation(self, eventbus):
        """测试错误传播机制"""
        error_messages = []

        def failing_processor(data, topic, source):
            if data.get("should_fail"):
                eventbus.publish("ERROR_OCCURRED", {
                    "error": "Processing failed",
                    "original_data": data,
                    "source": source
                })
            else:
                eventbus.publish("DATA_SUCCESS", {"result": "ok", "data": data})

        def error_handler(data, topic, source):
            error_messages.append(data)

        eventbus.subscribe("DATA_INPUT", failing_processor)
        eventbus.subscribe("ERROR_OCCURRED", error_handler)

        # 测试正常处理
        eventbus.publish("data_input", {"value": 100})
        assert len(error_messages) == 0

        # 测试错误处理
        eventbus.publish("data_input", {"value": 200, "should_fail": True})
        assert len(error_messages) == 1
        assert error_messages[0]["error"] == "Processing failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])