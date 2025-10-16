"""
测试数据库连接
"""
import asyncio
from sqlalchemy import text
from app.config.settings import get_settings


async def test_connection():
    settings = get_settings()
    print(f"DATABASE_URL: {settings.DATABASE_URL}")

    if not settings.DATABASE_URL:
        print("DATABASE_URL未配置")
        return

    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args={"ssl": False},
        )

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"数据库连接成功: {result.scalar()}")

        await engine.dispose()
        print("测试完成")

    except Exception as e:
        print(f"数据库连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_connection())
