"""
数据库连接和会话管理
"""
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from app.models.base import Base
from app.config.settings import get_settings

# 从Settings读取数据库URL
settings = get_settings()
DATABASE_URL = settings.DATABASE_URL or "postgresql://gateway_user:gateway_pass_2025@localhost:5432/apigateway"

# 异步引擎（用于生产环境）
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"ssl": False},  # 禁用SSL连接
)

# 同步引擎（用于迁移和测试）
sync_engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 同步会话工厂
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    异步数据库会话依赖注入
    用于FastAPI依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    同步数据库会话
    用于迁移脚本和测试
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await async_engine.dispose()


__all__ = [
    "async_engine",
    "sync_engine",
    "AsyncSessionLocal",
    "SessionLocal",
    "get_db",
    "get_sync_db",
    "init_db",
    "close_db",
]
