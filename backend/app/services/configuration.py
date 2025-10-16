"""
配置管理服务
从数据库加载配置并缓存到Redis
"""
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import RedisClient
from app.repositories.data_source import DataSourceRepository
from app.repositories.target_system import TargetSystemRepository
from app.repositories.routing_rule import RoutingRuleRepository
from app.repositories.frame_schema import FrameSchemaRepository
from app.models.data_source import DataSource
from app.models.target_system import TargetSystem
from app.models.routing_rule import RoutingRule
from app.models.frame_schema import FrameSchema
from app.core.eventbus.topics import TopicCategory
from app.core.eventbus import get_eventbus


class ConfigurationService:
    """配置管理服务"""

    # 缓存键前缀
    CACHE_PREFIX_DATA_SOURCE = "config:data_source:"
    CACHE_PREFIX_TARGET_SYSTEM = "config:target_system:"
    CACHE_PREFIX_ROUTING_RULE = "config:routing_rule:"
    CACHE_PREFIX_FRAME_SCHEMA = "config:frame_schema:"

    # 缓存过期时间(秒)
    CACHE_TTL = 3600  # 1小时

    def __init__(self, session: AsyncSession, redis: RedisClient):
        self.session = session
        self.redis = redis

        # 初始化Repository
        self.data_source_repo = DataSourceRepository(session)
        self.target_system_repo = TargetSystemRepository(session)
        self.routing_rule_repo = RoutingRuleRepository(session)
        self.frame_schema_repo = FrameSchemaRepository(session)

    async def load_all_configs(self) -> Dict[str, Any]:
        """加载所有配置到Redis缓存"""
        data_sources = await self.data_source_repo.get_active_sources()
        target_systems = await self.target_system_repo.get_active_targets()
        routing_rules = await self.routing_rule_repo.get_active_rules()
        frame_schemas = await self.frame_schema_repo.get_published_schemas()

        # 缓存数据源
        for ds in data_sources:
            await self.redis.set(
                f"{self.CACHE_PREFIX_DATA_SOURCE}{ds.id}",
                ds.to_dict(),
                self.CACHE_TTL,
            )

        # 缓存目标系统
        for ts in target_systems:
            await self.redis.set(
                f"{self.CACHE_PREFIX_TARGET_SYSTEM}{ts.id}",
                ts.to_dict(),
                self.CACHE_TTL,
            )

        # 缓存路由规则
        for rr in routing_rules:
            await self.redis.set(
                f"{self.CACHE_PREFIX_ROUTING_RULE}{rr.id}",
                rr.to_dict(),
                self.CACHE_TTL,
            )

        # 缓存帧格式
        for fs in frame_schemas:
            await self.redis.set(
                f"{self.CACHE_PREFIX_FRAME_SCHEMA}{fs.id}",
                fs.to_dict(),
                self.CACHE_TTL,
            )

        # 发布配置更新事件
        event_bus = get_eventbus()
        event_bus.publish(
            TopicCategory.CONFIG_UPDATED.value,
            {
                "data_sources": len(data_sources),
                "target_systems": len(target_systems),
                "routing_rules": len(routing_rules),
                "frame_schemas": len(frame_schemas),
            },
            source="ConfigurationService",
        )

        return {
            "data_sources": len(data_sources),
            "target_systems": len(target_systems),
            "routing_rules": len(routing_rules),
            "frame_schemas": len(frame_schemas),
        }

    async def get_data_source(self, id: UUID) -> Optional[Dict]:
        """获取数据源配置(优先从缓存)"""
        cache_key = f"{self.CACHE_PREFIX_DATA_SOURCE}{id}"

        # 尝试从缓存获取
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 从数据库获取
        ds = await self.data_source_repo.get(id)
        if ds:
            data = ds.to_dict()
            await self.redis.set(cache_key, data, self.CACHE_TTL)
            return data

        return None

    async def get_target_system(self, id: UUID) -> Optional[Dict]:
        """获取目标系统配置(优先从缓存)"""
        cache_key = f"{self.CACHE_PREFIX_TARGET_SYSTEM}{id}"

        # 尝试从缓存获取
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 从数据库获取
        ts = await self.target_system_repo.get(id)
        if ts:
            data = ts.to_dict()
            await self.redis.set(cache_key, data, self.CACHE_TTL)
            return data

        return None

    async def get_routing_rules(self) -> List[Dict]:
        """获取所有激活的路由规则"""
        rules = await self.routing_rule_repo.get_active_rules()
        return [rule.to_dict() for rule in rules]

    async def get_frame_schema(self, id: UUID) -> Optional[Dict]:
        """获取帧格式配置(优先从缓存)"""
        cache_key = f"{self.CACHE_PREFIX_FRAME_SCHEMA}{id}"

        # 尝试从缓存获取
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 从数据库获取
        fs = await self.frame_schema_repo.get(id)
        if fs:
            data = fs.to_dict()
            await self.redis.set(cache_key, data, self.CACHE_TTL)
            return data

        return None

    async def invalidate_data_source(self, id: UUID):
        """失效数据源缓存"""
        cache_key = f"{self.CACHE_PREFIX_DATA_SOURCE}{id}"
        await self.redis.delete(cache_key)

    async def invalidate_target_system(self, id: UUID):
        """失效目标系统缓存"""
        cache_key = f"{self.CACHE_PREFIX_TARGET_SYSTEM}{id}"
        await self.redis.delete(cache_key)

    async def invalidate_routing_rule(self, id: UUID):
        """失效路由规则缓存"""
        cache_key = f"{self.CACHE_PREFIX_ROUTING_RULE}{id}"
        await self.redis.delete(cache_key)

    async def invalidate_frame_schema(self, id: UUID):
        """失效帧格式缓存"""
        cache_key = f"{self.CACHE_PREFIX_FRAME_SCHEMA}{id}"
        await self.redis.delete(cache_key)

    async def invalidate_all(self):
        """失效所有配置缓存"""
        patterns = [
            f"{self.CACHE_PREFIX_DATA_SOURCE}*",
            f"{self.CACHE_PREFIX_TARGET_SYSTEM}*",
            f"{self.CACHE_PREFIX_ROUTING_RULE}*",
            f"{self.CACHE_PREFIX_FRAME_SCHEMA}*",
        ]

        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            for key in keys:
                await self.redis.delete(key)


__all__ = ["ConfigurationService"]
