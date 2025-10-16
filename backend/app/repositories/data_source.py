"""
数据源Repository
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSource
from app.schemas.common import ProtocolType
from .base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """数据源Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(DataSource, session)

    async def get_by_protocol(
        self, protocol_type: ProtocolType, is_active: bool = True
    ) -> List[DataSource]:
        """根据协议类型获取数据源"""
        stmt = select(self.model).where(
            self.model.protocol_type == protocol_type.value,
            self.model.is_active == is_active,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_sources(self) -> List[DataSource]:
        """获取所有激活的数据源"""
        stmt = select(self.model).where(self.model.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_message_count(self, id: UUID) -> None:
        """增加消息计数"""
        from datetime import datetime
        from sqlalchemy import update, func

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(
                total_messages=func.coalesce(self.model.total_messages, 0) + 1,
                last_message_at=datetime.utcnow(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()


__all__ = ["DataSourceRepository"]
