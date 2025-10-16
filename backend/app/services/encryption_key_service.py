"""加密密钥服务"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.encryption_key import EncryptionKey
from app.repositories.encryption_key import EncryptionKeyRepository
from app.services.crypto_service import get_crypto_service


class EncryptionKeyError(Exception):
    """密钥服务异常"""


class EncryptionKeyService:
    """密钥管理业务逻辑"""

    def __init__(self):
        self._crypto_service = get_crypto_service()

    def _get_session(self) -> AsyncSession:
        return AsyncSessionLocal()

    async def list_keys(self) -> List[EncryptionKey]:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)
            return await repo.list_keys()

    async def create_key(
        self,
        name: str,
        description: Optional[str] = None,
        key_material: Optional[bytes] = None,
        is_active: bool = False,
        metadata: Optional[dict] = None,
        expires_at: Optional[datetime] = None,
    ) -> EncryptionKey:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)

            existing = await repo.get_by_name(name)
            if existing:
                raise EncryptionKeyError("Key name already exists")

            key_bytes = key_material or os.urandom(32)

            record = EncryptionKey(
                id=uuid4(),
                name=name,
                description=description,
                key_material=key_bytes,
                is_active=is_active,
                extra=metadata or {},
                expires_at=expires_at,
            )
            record.updated_at = record.created_at

            if is_active:
                await repo.deactivate_all()
                record.is_active = True
                record.rotated_at = datetime.now(timezone.utc)
                record.updated_at = record.rotated_at

            session.add(record)
            await session.commit()
            await session.refresh(record)

            if record.is_active:
                self._crypto_service.update_active_key(bytes(record.key_material))

            return record

    async def activate_key(self, key_id: UUID) -> EncryptionKey:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)
            key = await repo.get(key_id)
            if not key:
                raise EncryptionKeyError("Key not found")

            await repo.deactivate_all()
            key.is_active = True
            key.rotated_at = datetime.now(timezone.utc)
            key.updated_at = key.rotated_at
            await session.commit()
            await session.refresh(key)

            self._crypto_service.update_active_key(bytes(key.key_material))
            return key

    async def deactivate_key(self, key_id: UUID) -> EncryptionKey:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)
            key = await repo.get(key_id)
            if not key:
                raise EncryptionKeyError("Key not found")

            key.is_active = False
            key.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(key)

            active = await repo.get_active()
            if not active:
                self._crypto_service.update_active_key(None)

            return key

    async def delete_key(self, key_id: UUID) -> None:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)
            key = await repo.get(key_id)
            if not key:
                raise EncryptionKeyError("Key not found")
            if key.is_active:
                raise EncryptionKeyError("Cannot delete active key")

            await session.delete(key)
            await session.commit()

    async def get_active_key(self) -> Optional[EncryptionKey]:
        async with self._get_session() as session:
            repo = EncryptionKeyRepository(session)
            return await repo.get_active()


_encryption_key_service: Optional[EncryptionKeyService] = None


def get_encryption_key_service() -> EncryptionKeyService:
    global _encryption_key_service
    if _encryption_key_service is None:
        _encryption_key_service = EncryptionKeyService()
    return _encryption_key_service
