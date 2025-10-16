"""加密密钥仓储"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encryption_key import EncryptionKey
from .base import BaseRepository


class EncryptionKeyRepository(BaseRepository[EncryptionKey]):
    """加密密钥仓储"""

    def __init__(self, session: AsyncSession):
        super().__init__(EncryptionKey, session)

    async def list_keys(self) -> List[EncryptionKey]:
        stmt = select(self.model).order_by(self.model.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[EncryptionKey]:
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active(self) -> Optional[EncryptionKey]:
        stmt = select(self.model).where(self.model.is_active.is_(True)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def deactivate_all(self) -> None:
        stmt = update(self.model).values(is_active=False)
        await self.session.execute(stmt)


__all__ = ["EncryptionKeyRepository"]
