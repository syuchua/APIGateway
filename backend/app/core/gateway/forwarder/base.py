"""
转发器基类
定义所有转发器的统一接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from app.schemas.forwarder import ForwardResult


class BaseForwarder(ABC):
    """
    转发器抽象基类

    所有转发器必须继承此类并实现抽象方法

    职责：
    - 将数据转发到目标系统
    - 处理重试和错误
    - 提供批量转发能力
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化转发器

        Args:
            config: 转发器配置字典
        """
        self.config = config

        # 统计信息
        self._stats = {
            "forwards_attempted": 0,
            "forwards_succeeded": 0,
            "forwards_failed": 0,
            "total_duration_ms": 0.0
        }

    @abstractmethod
    async def forward(self, data: Dict[str, Any]) -> ForwardResult:
        """
        转发单条数据

        Args:
            data: 要转发的数据

        Returns:
            转发结果

        Raises:
            Exception: 转发失败时可能抛出异常
        """
        pass

    @abstractmethod
    async def forward_batch(self, data_list: List[Dict[str, Any]]) -> List[ForwardResult]:
        """
        批量转发数据

        Args:
            data_list: 要转发的数据列表

        Returns:
            转发结果列表
        """
        pass

    @abstractmethod
    async def close(self):
        """
        关闭连接，释放资源

        应该优雅地关闭所有连接
        """
        pass

    def get_stats(self) -> Dict[str, Any]:
        """
        获取转发器统计信息

        Returns:
            包含统计数据的字典
        """
        return {
            **self._stats,
            "success_rate": (
                self._stats["forwards_succeeded"] / self._stats["forwards_attempted"]
                if self._stats["forwards_attempted"] > 0
                else 0.0
            ),
            "avg_duration_ms": (
                self._stats["total_duration_ms"] / self._stats["forwards_attempted"]
                if self._stats["forwards_attempted"] > 0
                else 0.0
            )
        }

    def _increment_stats(self, key: str, value: float = 1.0):
        """
        增加统计计数

        Args:
            key: 统计项名称
            value: 增加的值
        """
        if key in self._stats:
            self._stats[key] += value
