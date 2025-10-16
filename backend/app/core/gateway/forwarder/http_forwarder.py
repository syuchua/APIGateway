"""
HTTP转发器实现
使用httpx异步发送HTTP请求到目标系统
"""
import logging
import asyncio
import time
import base64
from datetime import datetime
from typing import Dict, Any, List

import httpx

from app.schemas.forwarder import (
    HTTPForwarderConfig,
    ForwardResult,
    ForwardStatus
)
from app.core.gateway.forwarder.base import BaseForwarder

logger = logging.getLogger(__name__)


class HTTPForwarder(BaseForwarder):
    """
    HTTP转发器

    功能：
    - 异步发送HTTP请求
    - 支持多种HTTP方法(GET/POST/PUT/PATCH/DELETE)
    - 自动重试机制
    - 超时处理
    - 批量转发
    - 错误处理
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化HTTP转发器

        Args:
            config: 转发器配置字典（兼容HTTPForwarderConfig）
        """
        # 调用父类初始化
        super().__init__(config)

        # 如果config是字典，转换为HTTPForwarderConfig
        if isinstance(config, dict):
            self.http_config = HTTPForwarderConfig(**config)
        elif isinstance(config, HTTPForwarderConfig):
            self.http_config = config
        else:
            raise TypeError("config must be dict or HTTPForwarderConfig")

        # 创建httpx异步客户端
        client_kwargs = {
            "timeout": httpx.Timeout(self.http_config.timeout),
            "verify": self.http_config.verify_ssl,
            # 避免读取系统代理（如 socks://），影响本地内网转发
            "trust_env": False,
        }

        # 添加认证
        if self.http_config.username and self.http_config.password:
            client_kwargs["auth"] = (self.http_config.username, self.http_config.password)

        self.client = httpx.AsyncClient(**client_kwargs)

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

        prepared_payload = self._prepare_json_payload(data)

        for attempt in range(self.http_config.retry_times + 1):
            try:
                # 构建请求参数
                request_kwargs = {
                    "url": self.http_config.url,
                    "json": prepared_payload,
                }

                # 添加自定义请求头
                if self.http_config.headers:
                    request_kwargs["headers"] = self.http_config.headers

                # 根据方法调用相应的HTTP方法
                method_func = getattr(self.client, self.http_config.method.lower())
                response = await method_func(**request_kwargs)

                # 计算耗时
                duration = time.time() - start_time

                # 检查响应状态
                if 200 <= response.status_code < 300:
                    logger.info(
                        f"HTTP转发成功: {self.http_config.url}, "
                        f"状态码: {response.status_code}, "
                        f"耗时: {duration:.2f}s"
                    )

                    # 更新统计
                    self._increment_stats("forwards_succeeded")
                    self._increment_stats("total_duration_ms", duration * 1000)

                    return ForwardResult(
                        status=ForwardStatus.SUCCESS,
                        status_code=response.status_code,
                        response_text=response.text[:500],  # 限制响应文本长度
                        retry_count=retry_count,
                        duration=duration
                    )
                else:
                    # HTTP错误状态码
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"HTTP转发失败: {error_msg}")

                    # 如果还有重试机会，继续重试
                    if attempt < self.http_config.retry_times:
                        retry_count += 1
                        await asyncio.sleep(self.http_config.retry_delay)
                        continue

                    # 更新统计
                    self._increment_stats("forwards_failed")
                    self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                    return ForwardResult(
                        status=ForwardStatus.FAILED,
                        status_code=response.status_code,
                        response_text=response.text[:500],
                        error=error_msg,
                        retry_count=retry_count,
                        duration=time.time() - start_time
                    )

            except httpx.TimeoutException as e:
                logger.warning(f"HTTP转发超时: {self.http_config.url}, 尝试 {attempt + 1}/{self.http_config.retry_times + 1}")

                if attempt < self.http_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.http_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.TIMEOUT,
                    error=f"Request timeout after {self.http_config.timeout}s",
                    retry_count=retry_count,
                    duration=time.time() - start_time
                )

            except (httpx.ConnectError, httpx.NetworkError) as e:
                logger.warning(f"HTTP转发网络错误: {e}, 尝试 {attempt + 1}/{self.http_config.retry_times + 1}")

                if attempt < self.http_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.http_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.FAILED,
                    error=f"Network error: {str(e)}",
                    retry_count=retry_count,
                    duration=time.time() - start_time
                )

            except Exception as e:
                logger.error(f"HTTP转发未知错误: {e}", exc_info=True)

                if attempt < self.http_config.retry_times:
                    retry_count += 1
                    await asyncio.sleep(self.http_config.retry_delay)
                    continue

                # 更新统计
                self._increment_stats("forwards_failed")
                self._increment_stats("total_duration_ms", (time.time() - start_time) * 1000)

                return ForwardResult(
                    status=ForwardStatus.FAILED,
                    error=f"Unknown error: {str(e)}",
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
        """关闭HTTP客户端"""
        await self.client.aclose()

    def _prepare_json_payload(self, payload: Any) -> Any:
        """将转发数据转换为可JSON序列化的结构"""

        if isinstance(payload, dict):
            return {k: self._prepare_json_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self._prepare_json_payload(item) for item in payload]
        if isinstance(payload, tuple):
            return [self._prepare_json_payload(item) for item in payload]
        if isinstance(payload, (bytes, bytearray)):
            if not payload:
                return ""
            return base64.b64encode(bytes(payload)).decode("ascii")
        if isinstance(payload, datetime):
            return payload.isoformat()
        return payload
        logger.info("HTTP转发器已关闭")
