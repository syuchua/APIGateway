#!/usr/bin/env python3
"""
清理数据库中的所有测试数据
"""
import asyncio
from sqlalchemy import text
import sys
sys.path.insert(0, '/home/yuchu/workspace/APIGateway/backend')

from app.db.database import async_engine


async def clean_all_data():
    """清理所有表的数据"""
    print("⚠️  警告：即将清理数据库中的所有数据！")
    print("正在清理...")

    async with async_engine.begin() as conn:
        # 按照依赖关系的逆序删除数据（先删除引用其他表的数据）

        # 定义要清理的表（按依赖顺序）
        tables = [
            ('gateway.routing_rules', '路由规则'),
            ('gateway.forward_logs', '转发日志'),
            ('gateway.message_logs', '消息日志'),
            ('gateway.target_systems', '目标系统'),
            ('gateway.data_sources', '数据源'),
            ('gateway.frame_schemas', '帧格式'),
        ]

        for table_name, display_name in tables:
            try:
                result = await conn.execute(text(f'DELETE FROM {table_name}'))
                print(f"✅ 已删除 {result.rowcount} 条{display_name}")
            except Exception as e:
                if 'does not exist' in str(e):
                    print(f"⏭️  跳过不存在的表: {table_name}")
                else:
                    print(f"❌ 删除 {table_name} 失败: {e}")

    print("\n✅ 数据库清理完成！")

    # 验证清理结果
    async with async_engine.begin() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM gateway.data_sources'))
        ds_count = result.scalar()

        result = await conn.execute(text('SELECT COUNT(*) FROM gateway.target_systems'))
        ts_count = result.scalar()

        result = await conn.execute(text('SELECT COUNT(*) FROM gateway.routing_rules'))
        rr_count = result.scalar()

        print(f"\n当前数据库状态:")
        print(f"  数据源: {ds_count}")
        print(f"  目标系统: {ts_count}")
        print(f"  路由规则: {rr_count}")


if __name__ == "__main__":
    asyncio.run(clean_all_data())
