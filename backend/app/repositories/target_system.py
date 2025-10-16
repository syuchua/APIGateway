"""
目标系统Repository
"""
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target_system import TargetSystem
from app.schemas.common import ProtocolType
from .base import BaseRepository


class TargetSystemRepository(BaseRepository[TargetSystem]):
    """目标系统Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(TargetSystem, session)

    async def get_by_protocol(
        self, protocol_type: ProtocolType, is_active: bool = True
    ) -> List[TargetSystem]:
        """根据协议类型获取目标系统"""
        stmt = select(self.model).where(
            self.model.protocol_type == protocol_type.value,
            self.model.is_active == is_active,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_targets(self) -> List[TargetSystem]:
        """获取所有激活的目标系统"""
        stmt = select(self.model).where(self.model.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_forward_count(
        self, id: UUID, success: bool = True
    ) -> None:
        """增加转发计数"""
        from datetime import datetime
        from sqlalchemy import update, func

        if success:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(
                    total_forwarded=func.coalesce(self.model.total_forwarded, 0) + 1,
                    last_forward_at=datetime.utcnow(),
                )
            )
        else:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(
                    total_failed=func.coalesce(self.model.total_failed, 0) + 1,
                    last_forward_at=datetime.utcnow(),
                )
            )

        await self.session.execute(stmt)
        await self.session.flush()


__all__ = ["TargetSystemRepository"]
