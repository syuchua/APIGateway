"""
用户服务
"""
import logging
from datetime import datetime

from app.config.settings import get_settings
from app.core.security.auth import auth_service
from app.db.database import AsyncSessionLocal
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


async def ensure_default_admin_user() -> None:
    """
    确保默认管理员存在
    在系统初始化时调用
    """
    settings = get_settings()

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_username(settings.DEFAULT_ADMIN_USERNAME)
        if existing:
            return

        password_hash = auth_service.get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)

        await repo.create(
            username=settings.DEFAULT_ADMIN_USERNAME,
            email=settings.DEFAULT_ADMIN_EMAIL,
            full_name=settings.DEFAULT_ADMIN_FULL_NAME,
            password_hash=password_hash,
            role="admin",
            is_active=True,
            avatar=None,
        )
        await session.commit()

    logger.info(
        "Default admin user `%s` initialized.",
        settings.DEFAULT_ADMIN_USERNAME,
    )


__all__ = ["ensure_default_admin_user"]
