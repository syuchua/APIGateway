"""
Redis缓存管理
"""
import json
import os
from typing import Optional, Any

import redis.asyncio as aioredis
from redis.asyncio import Redis


class RedisClient:
    """Redis异步客户端"""

    def __init__(self):
        self.client: Optional[Redis] = None
        self.url = os.getenv("REDIS_URL", "redis://:redis_pass_2025@localhost:6379/0")

    async def connect(self):
        """连接Redis"""
        if not self.client:
            self.client = await aioredis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.client:
            await self.connect()

        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> bool:
        """设置缓存"""
        if not self.client:
            await self.connect()

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if expire:
            return await self.client.setex(key, expire, value)
        else:
            return await self.client.set(key, value)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.client:
            await self.connect()

        result = await self.client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            await self.connect()

        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self.client:
            await self.connect()

        return await self.client.expire(key, seconds)

    async def keys(self, pattern: str) -> list:
        """获取匹配的键"""
        if not self.client:
            await self.connect()

        return await self.client.keys(pattern)

    async def flushdb(self):
        """清空当前数据库"""
        if not self.client:
            await self.connect()

        await self.client.flushdb()


# 全局Redis客户端实例
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """获取Redis客户端(依赖注入)"""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client


__all__ = ["RedisClient", "redis_client", "get_redis"]
