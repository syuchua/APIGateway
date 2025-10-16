"""
高性能EventBus消息总线实现
基于测试驱动开发(TDD)，替代MQTT内部消息总线
零网络开销，纯内存操作，支持通配符订阅
"""
import threading
import uuid
import fnmatch
import logging
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
from functools import wraps

logger = logging.getLogger(__name__)


class EventSubscriber:
    """事件订阅装饰器"""

    def __init__(self, topic: str):
        self.topic = topic

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(data, topic, source):
            return func(data, topic, source)

        wrapper.topic = self.topic
        wrapper.original_func = func

        def register(eventbus, instance=None):
            if instance is not None:
                # 绑定实例方法
                bound_method = lambda data, topic, source: func(instance, data, topic, source)
                return eventbus.subscribe(self.topic, bound_method)
            else:
                return eventbus.subscribe(self.topic, wrapper)

        wrapper.register = register
        return wrapper


class SimpleEventBus:
    """
    高性能EventBus实现

    特性：
    - 零网络开销：纯内存操作
    - 线程安全：使用RLock保护
    - 通配符支持：支持 * 通配符订阅
    - 异常隔离：单个回调异常不影响其他回调
    - 高性能：目标 >100万 msg/s
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.RLock()
        self._subscriber_index: Dict[str, Dict] = {}

    def subscribe(self, topic: str, callback: Callable) -> str:
        """
        订阅主题

        Args:
            topic: 主题名称，建议使用全大写字母+下划线格式 (DATA_RECEIVED, UDP_MESSAGE等)
                  支持通配符 (DATA_*)
            callback: 回调函数，签名为 callback(data, topic, source)

        Returns:
            str: 订阅ID，用于取消订阅
        """
        # 规范化主题名称为大写
        topic = topic.upper()

        subscriber_id = str(uuid.uuid4())

        subscriber_info = {
            'id': subscriber_id,
            'callback': callback,
            'topic': topic
        }

        with self._lock:
            self._subscribers[topic].append(subscriber_info)
            self._subscriber_index[subscriber_id] = {
                'topic': topic,
                'info': subscriber_info
            }

        logger.info(f"订阅主题: {topic}, ID: {subscriber_id}")
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        取消订阅

        Args:
            subscriber_id: 订阅ID

        Returns:
            bool: 是否成功取消订阅
        """
        with self._lock:
            if subscriber_id not in self._subscriber_index:
                return False

            subscriber_data = self._subscriber_index[subscriber_id]
            topic = subscriber_data['topic']
            subscriber_info = subscriber_data['info']

            # 从订阅列表中移除
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(subscriber_info)
                    if not self._subscribers[topic]:
                        del self._subscribers[topic]
                except ValueError:
                    pass

            # 从索引中移除
            del self._subscriber_index[subscriber_id]

        logger.info(f"取消订阅: {subscriber_id}")
        return True

    def publish(self, topic: str, data: Any, source: Optional[str] = None) -> int:
        """
        发布消息

        Args:
            topic: 主题名称，会自动转换为大写格式
            data: 消息数据
            source: 消息来源（可选）

        Returns:
            int: 成功调用的回调数量
        """
        # 规范化主题名称为大写
        topic = topic.upper()
        executed_count = 0

        with self._lock:
            # 收集匹配的订阅者
            matched_subscribers = []

            # 精确匹配
            if topic in self._subscribers:
                matched_subscribers.extend(self._subscribers[topic])

            # 通配符匹配
            for subscribed_topic, subscribers in self._subscribers.items():
                if '*' in subscribed_topic and fnmatch.fnmatch(topic, subscribed_topic):
                    matched_subscribers.extend(subscribers)

        # 执行回调（在锁外执行以提高性能）
        for subscriber in matched_subscribers:
            try:
                subscriber['callback'](data, topic, source)
                executed_count += 1
            except Exception as e:
                logger.error(f"回调执行失败: {subscriber.get('id', 'unknown')}, 错误: {e}")
                executed_count += 1  # 仍然计算为已执行，只是失败了

        if executed_count > 0:
            logger.info(f"发布消息到主题: {topic}, 执行回调: {executed_count}")

        return executed_count

    def get_subscribers_count(self, topic: Optional[str] = None) -> int:
        """
        获取订阅者数量

        Args:
            topic: 指定主题，None表示所有主题

        Returns:
            int: 订阅者数量
        """
        with self._lock:
            if topic is None:
                return sum(len(subscribers) for subscribers in self._subscribers.values())
            return len(self._subscribers.get(topic, []))

    def get_topics(self) -> List[str]:
        """获取所有已订阅的主题列表"""
        with self._lock:
            return list(self._subscribers.keys())

    def clear(self):
        """清空所有订阅"""
        with self._lock:
            self._subscribers.clear()
            self._subscriber_index.clear()
        logger.info("已清空所有订阅")


# 全局EventBus实例
_global_eventbus = None
_eventbus_lock = threading.Lock()


def get_eventbus() -> SimpleEventBus:
    """获取全局EventBus实例（单例模式）"""
    global _global_eventbus

    if _global_eventbus is None:
        with _eventbus_lock:
            if _global_eventbus is None:
                _global_eventbus = SimpleEventBus()
                logger.info("创建全局EventBus实例")

    return _global_eventbus


def reset_eventbus():
    """
    重置全局EventBus实例

    警告：仅用于测试！会清除所有订阅者和消息历史
    """
    global _global_eventbus

    with _eventbus_lock:
        _global_eventbus = None
        logger.info("全局EventBus已重置")


def publish(topic: str, data: Any, source: Optional[str] = None) -> int:
    """发布消息到全局EventBus"""
    return get_eventbus().publish(topic, data, source)


def subscribe(topic: str, callback: Callable) -> str:
    """订阅全局EventBus主题"""
    return get_eventbus().subscribe(topic, callback)


def unsubscribe(subscriber_id: str) -> bool:
    """取消订阅全局EventBus"""
    return get_eventbus().unsubscribe(subscriber_id)


# 性能监控装饰器
def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start_time

        # 发布性能指标
        get_eventbus().publish("metrics.performance", {
            "function": func.__name__,
            "duration_ms": duration * 1000,
            "timestamp": time.time()
        }, source="performance_monitor")

        return result
    return wrapper


if __name__ == "__main__":
    # 简单测试
    import time

    def test_callback(data, topic, source):
        print(f"接收消息: {data}, 主题: {topic}, 来源: {source}")

    # 创建EventBus
    bus = SimpleEventBus()

    # 订阅
    sub_id = bus.subscribe("TEST_*", test_callback)

    # 发布消息
    bus.publish("test_message", {"hello": "world"}, "test_source")

    # 性能测试
    start = time.time()
    for i in range(100000):
        bus.publish("test_perf", {"index": i})
    duration = time.time() - start

    print(f"性能测试: 100,000条消息耗时 {duration:.3f}秒")
    print(f"吞吐量: {100000/duration:.0f} msg/s")

    # 清理
    bus.unsubscribe(sub_id)