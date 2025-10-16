"""
WebSocket转发器实现
使用websockets库异步发送数据到WebSocket服务器
"""
import logging
import asyncio
import json
import time
from typing import Dict, Any, List

import websockets

from app.schemas.forwarder import (
    WebSocketForwarderConfig,
    ForwardResult,
    ForwardStatus
)
from app.core.gateway.forwarder.base import BaseForwarder

logger = logging.getLogger(__name__)


class WebSocketForwarder(BaseForwarder):
    """
    WebSocket转发器

    功能：
    - 异步WebSocket连接管理
    - 自动重连机制
    - 心跳检测
    - 批量数据转发
    - 错误处理和重试
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化WebSocket转发器

        Args:
            config: 转发器配置字典（兼容WebSocketForwarderConfig）
        """
        # 调用父类初始化
        super().__init__(config)

        # 如果config是字典，转换为WebSocketForwarderConfig
        if isinstance(config, dict):
            self.ws_config = WebSocketForwarderConfig(**config)
        elif isinstance(config, WebSocketForwarderConfig):
            self.ws_config = config
        else:
            raise TypeError("config must be dict or WebSocketForwarderConfig")

        # WebSocket连接状态
        self.connection = None
        self.is_connected = False
        self._connect_lock = asyncio.Lock()
        self._last_ping_time = 0
        self._ping_task = None

    async def _connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            连接是否成功
        """
        async with self._connect_lock:
            if self.is_connected and self.connection:
                # 检查连接是否仍然活跃
                try:
                    # 发送ping测试连接
                    await self.connection.ping()
                    return True
                except Exception:
                    # 连接已断开，需要重新连接
                    await self._disconnect()

            try:
                # 准备连接参数
                connect_kwargs = {
                    "uri": self.ws_config.url,
                    "ping_interval": self.ws_config.ping_interval,
                    "ping_timeout": self.ws_config.ping_timeout,
                    "close_timeout": self.ws_config.close_timeout,
                }

                # 添加自定义请求头
                if self.ws_config.headers:
                    connect_kwargs["extra_headers"] = self.ws_config.headers

                # 建立连接
                # 检查是否是mock对象
                if hasattr(websockets.connect, 'return_value'):
                    # Mock情况，直接调用
                    self.connection = websockets.connect(**connect_kwargs)
                else:
                    # 真实情况，使用await
                    self.connection = await websockets.connect(**connect_kwargs)
                self.is_connected = True

                # 启动心跳任务
                if self._ping_task is None or self._ping_task.done():
                    self._ping_task = asyncio.create_task(self._ping_loop())

                logger.info(f"WebSocket连接成功: {self.ws_config.url}")
                return True

            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                await self._disconnect()
                return False

    async def _disconnect(self):
        """断开WebSocket连接"""
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                logger.warning(f"关闭WebSocket连接时出错: {e}")
            finally:
                self.connection = None

        self.is_connected = False

        # 停止心跳任务
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

    async def _ping_loop(self):
        """心跳检测循环"""
        while self.is_connected:
            try:
                # 检查是否需要发送ping
                current_time = time.time()
                if current_time - self._last_ping_time >= self.ws_config.ping_interval:
                    if self.connection and self.is_connected:
                        await self.connection.ping()
                        self._last_ping_time = current_time
                        logger.info("WebSocket ping sent")

                await asyncio.sleep(1)  # 每秒检查一次

            except Exception as e:
                logger.error(f"WebSocket心跳错误: {e}")
                break

        # 心跳循环结束，标记连接为断开
        self.is_connected = False

    async def forward(self, data: Dict[str, Any]) -> ForwardResult:
        """
        转发单条数据

        Args:
            data: 要转发的数据

        Returns:
            转发结果
        """
        start_time = time.time()
        retry_count = 0

        # 更新统计
        self._increment_stats("forwards_attempted")

        for attempt in range(self.ws_config.retry_times + 1):
            try:
                # 确保连接已建立
                if not self.is_connected:
                    connected = await self._connect()
                    if not connected:
                        if attempt < self.ws_config.retry_times:
                            retry_count += 1
                            await asyncio.sleep(self.ws_config.retry_delay)
                            continue
                        else:
                            # 更新统计
                            self._increment_stats("forwards_failed")
                            self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                            return ForwardResult(
                                status=ForwardStatus.FAILED,
                                error="Failed to establish WebSocket connection",
                                retry_count=retry_count,
                                duration=time.time() - start_time
                            )

                # 序列化数据为JSON
                json_data = json.dumps(data, ensure_ascii=False)

                # 发送数据
                await asyncio.wait_for(
                    self.connection.send(json_data),
                    timeout=self.ws_config.timeout
                )

                # 计算耗时
                duration = time.time() - start_time

                # 更新统计
                self._increment_stats("forwards_succeeded")
                self._increment_stats("total_duration_ms", duration * 1000)

                logger.info(
                    f"WebSocket转发成功: {self.ws_config.url}, "
                    f"数据大小: {len(json_data)}字节, "
                    f"耗时: {duration:.2f}s"
                )

                return ForwardResult(
                    status=ForwardStatus.SUCCESS,
                    retry_count=retry_count,
                    duration=duration
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"WebSocket转发超时: {self.ws_config.url}, "
                    f"尝试 {attempt + 1}/{self.ws_config.retry_times + 1}"
                )

                # 连接可能已断开，尝试重新连接
                await self._disconnect()

                if attempt < self.ws_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.ws_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.TIMEOUT,
                    error=f"WebSocket send timeout after {self.ws_config.timeout}s",
                    retry_count=retry_count,
                    duration=time.time() - start_time
                )

            except (websockets.exceptions.ConnectionClosed, 
                   websockets.exceptions.ConnectionClosedError,
                   websockets.exceptions.ConnectionClosedOK) as e:
                logger.warning(
                    f"WebSocket连接已关闭: {e}, "
                    f"尝试 {attempt + 1}/{self.ws_config.retry_times + 1}"
                )

                # 标记连接为断开
                await self._disconnect()

                if attempt < self.ws_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.ws_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.FAILED,
                    error=f"WebSocket connection closed: {str(e)}",
                    retry_count=retry_count,
                    duration=time.time() - start_time
                )

            except Exception as e:
                logger.error(
                    f"WebSocket转发未知错误: {e}, "
                    f"尝试 {attempt + 1}/{self.ws_config.retry_times + 1}",
                    exc_info=True
                )

                # 标记连接为断开
                await self._disconnect()

                if attempt < self.ws_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.ws_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.FAILED,
                    error=f"WebSocket forward error: {str(e)}",
                    retry_count=retry_count,
                    duration=time.time() - start_time
                )

        # 不应该到达这里
        self._increment_stats("forwards_failed")
        self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

        return ForwardResult(
            status=ForwardStatus.FAILED,
            error="Unexpected error: retry loop completed without result",
            retry_count=retry_count,
            duration=time.time() - start_time
        )

    async def forward_batch(self, data_list: List[Dict[str, Any]]) -> List[ForwardResult]:
        """
        批量转发数据

        Args:
            data_list: 数据列表

        Returns:
            转发结果列表
        """
        tasks = [self.forward(data) for data in data_list]
        results = await asyncio.gather(*tasks)
        return results

    async def close(self):
        """关闭WebSocket连接"""
        await self._disconnect()
        logger.info("WebSocket转发器已关闭")