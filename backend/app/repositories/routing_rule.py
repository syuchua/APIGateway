"""
路由规则Repository
"""
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routing_rule import RoutingRule
from .base import BaseRepository


class RoutingRuleRepository(BaseRepository[RoutingRule]):
    """路由规则Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(RoutingRule, session)

    async def get_active_rules(self) -> List[RoutingRule]:
        """获取所有激活且已发布的路由规则,按优先级排序"""
        stmt = (
            select(self.model)
            .where(self.model.is_active == True, self.model.is_published == True)
            .order_by(self.model.priority.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_match_count(self, id: UUID) -> None:
        """增加匹配计数"""
        from datetime import datetime
        from sqlalchemy import update, func

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(
                match_count=func.coalesce(self.model.match_count, 0) + 1,
                last_match_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def publish(self, id: UUID) -> bool:
        """发布路由规则"""
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(is_published=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def unpublish(self, id: UUID) -> bool:
        """取消发布路由规则"""
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(is_published=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


__all__ = ["RoutingRuleRepository"]
