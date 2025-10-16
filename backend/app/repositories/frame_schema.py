"""
帧格式Repository
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.frame_schema import FrameSchema
from .base import BaseRepository


class FrameSchemaRepository(BaseRepository[FrameSchema]):
    """帧格式Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(FrameSchema, session)

    async def get_published_schemas(self) -> List[FrameSchema]:
        """获取所有已发布的帧格式"""
        stmt = select(self.model).where(self.model.is_published == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_version(
        self, name: str, version: str
    ) -> Optional[FrameSchema]:
        """根据名称和版本获取帧格式"""
        stmt = select(self.model).where(
            self.model.name == name, self.model.version == version
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def publish(self, id) -> bool:
        """发布帧格式"""
        from uuid import UUID
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(is_published=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


__all__ = ["FrameSchemaRepository"]
