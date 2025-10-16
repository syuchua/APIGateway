"""
简单的数据库连接测试
"""
import asyncio


async def test_postgres_connection():
    """测试PostgreSQL连接"""
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        print(f"[OK] PostgreSQL连接成功: {row[0]}")

        # 检查Schema
        result = await session.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'gateway'")
        )
        schema = result.fetchone()
        if schema:
            print(f"[OK] Gateway Schema存在")
        else:
            print("[FAIL] Gateway Schema不存在")

        # 检查表
        result = await session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'gateway'
                ORDER BY table_name
            """)
        )
        tables = result.fetchall()
        if tables:
            print(f"[OK] 找到{len(tables)}个表:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("[FAIL] 未找到表")


async def test_redis_connection():
    """测试Redis连接"""
    from app.db.redis import redis_client

    await redis_client.connect()

    # 测试set/get
    await redis_client.set("test_key", "hello_world", 60)
    value = await redis_client.get("test_key")
    print(f"[OK] Redis连接成功: {value}")

    # 清理
    await redis_client.delete("test_key")
    await redis_client.close()


async def main():
    print("=" * 50)
    print("数据库集成测试")
    print("=" * 50)

    print("\n1. 测试PostgreSQL连接...")
    try:
        await test_postgres_connection()
    except Exception as e:
        print(f"[FAIL] PostgreSQL连接失败: {e}")

    print("\n2. 测试Redis连接...")
    try:
        await test_redis_connection()
    except Exception as e:
        print(f"[FAIL] Redis连接失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
