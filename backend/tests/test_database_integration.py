"""
数据库集成测试
测试PostgreSQL和Redis的连接和基本操作
"""
import pytest
import asyncio
from uuid import uuid4

from app.db.database import AsyncSessionLocal, init_db, close_db
from app.db.redis import redis_client
from app.repositories import (
    DataSourceRepository,
    TargetSystemRepository,
    RoutingRuleRepository,
    FrameSchemaRepository,
)
from app.services.configuration import ConfigurationService


@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_database():
    """设置数据库"""
    # 初始化数据库表（如果不存在）
    # await init_db()  # 使用init_db.sql已创建,不需要再次创建

    yield

    # 清理
    await close_db()


@pytest.fixture
async def db_session():
    """数据库会话fixture"""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # 测试后回滚


@pytest.fixture
async def redis():
    """Redis客户端fixture"""
    await redis_client.connect()
    yield redis_client
    # 测试后清空测试数据
    await redis_client.flushdb()


class TestDatabaseConnection:
    """测试数据库连接"""

    @pytest.mark.asyncio
    async def test_postgres_connection(self, db_session, setup_database):
        """测试PostgreSQL连接"""
        # 执行简单查询
        from sqlalchemy import text

        result = await db_session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        assert row[0] == 1

    @pytest.mark.asyncio
    async def test_redis_connection(self, redis):
        """测试Redis连接"""
        # 测试set/get
        await redis.set("test_key", "test_value")
        value = await redis.get("test_key")
        assert value == "test_value"

        # 清理
        await redis.delete("test_key")


class TestDataSourceRepository:
    """测试数据源Repository"""

    @pytest.mark.asyncio
    async def test_create_data_source(self, db_session, setup_database):
        """测试创建数据源"""
        repo = DataSourceRepository(db_session)

        ds = await repo.create(
            name="Test UDP Source",
            description="Test UDP data source",
            protocol_type="udp",
            is_active=True,
            connection_config={
                "host": "0.0.0.0",
                "port": 8001,
                "buffer_size": 1024,
            },
        )

        assert ds.id is not None
        assert ds.name == "Test UDP Source"
        assert ds.protocol_type == "udp"

    @pytest.mark.asyncio
    async def test_get_data_source(self, db_session, setup_database):
        """测试获取数据源"""
        repo = DataSourceRepository(db_session)

        # 创建
        ds = await repo.create(
            name="Test HTTP Source",
            protocol_type="http",
            is_active=True,
            connection_config={"port": 8002},
        )

        # 获取
        fetched = await repo.get(ds.id)
        assert fetched is not None
        assert fetched.id == ds.id
        assert fetched.name == "Test HTTP Source"

    @pytest.mark.asyncio
    async def test_get_active_sources(self, db_session, setup_database):
        """测试获取激活的数据源"""
        repo = DataSourceRepository(db_session)

        # 创建激活的数据源
        await repo.create(
            name="Active Source 1",
            protocol_type="udp",
            is_active=True,
            connection_config={"port": 8001},
        )

        # 创建非激活的数据源
        await repo.create(
            name="Inactive Source",
            protocol_type="tcp",
            is_active=False,
            connection_config={"port": 8005},
        )

        # 获取激活的
        active_sources = await repo.get_active_sources()
        assert len(active_sources) >= 1
        assert all(ds.is_active for ds in active_sources)


class TestTargetSystemRepository:
    """测试目标系统Repository"""

    @pytest.mark.asyncio
    async def test_create_target_system(self, db_session, setup_database):
        """测试创建目标系统"""
        repo = TargetSystemRepository(db_session)

        ts = await repo.create(
            name="Test HTTP Target",
            description="Test HTTP target system",
            protocol_type="http",
            endpoint="http://localhost:9000/api/data",
            is_active=True,
            forwarder_config={
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "timeout": 30,
            },
        )

        assert ts.id is not None
        assert ts.name == "Test HTTP Target"
        assert ts.protocol_type == "http"


class TestRoutingRuleRepository:
    """测试路由规则Repository"""

    @pytest.mark.asyncio
    async def test_create_routing_rule(self, db_session, setup_database):
        """测试创建路由规则"""
        repo = RoutingRuleRepository(db_session)

        rr = await repo.create(
            name="Test Rule",
            description="Test routing rule",
            priority=50,
            conditions=[
                {"field": "source_protocol", "operator": "==", "value": "UDP"}
            ],
            logical_operator="AND",
            target_system_ids=[str(uuid4())],
            is_active=True,
            is_published=False,
        )

        assert rr.id is not None
        assert rr.name == "Test Rule"
        assert rr.priority == 50

    @pytest.mark.asyncio
    async def test_publish_rule(self, db_session, setup_database):
        """测试发布路由规则"""
        repo = RoutingRuleRepository(db_session)

        # 创建未发布的规则
        rr = await repo.create(
            name="Unpublished Rule",
            priority=50,
            conditions=[],
            target_system_ids=[str(uuid4())],
            is_active=True,
            is_published=False,
        )

        assert rr.is_published is False

        # 发布
        success = await repo.publish(rr.id)
        assert success is True

        # 验证
        fetched = await repo.get(rr.id)
        assert fetched.is_published is True


class TestFrameSchemaRepository:
    """测试帧格式Repository"""

    @pytest.mark.asyncio
    async def test_create_frame_schema(self, db_session, setup_database):
        """测试创建帧格式"""
        repo = FrameSchemaRepository(db_session)

        fs = await repo.create(
            name="Test Frame Schema",
            version="1.0.0",
            description="Test frame schema",
            protocol_type="udp",
            frame_type="fixed",
            total_length=32,
            fields=[
                {
                    "name": "header",
                    "data_type": "uint8",
                    "offset": 0,
                    "length": 2,
                    "byte_order": "big",
                },
                {
                    "name": "temperature",
                    "data_type": "float",
                    "offset": 2,
                    "length": 4,
                    "byte_order": "big",
                    "scale": 0.1,
                    "offset_value": 0.0,
                },
            ],
            checksum={"type": "crc16", "offset": 30, "length": 2},
            is_published=False,
        )

        assert fs.id is not None
        assert fs.name == "Test Frame Schema"
        assert fs.version == "1.0.0"


class TestConfigurationService:
    """测试配置管理服务"""

    @pytest.mark.asyncio
    async def test_load_all_configs(
        self, db_session, redis, setup_database
    ):
        """测试加载所有配置"""
        # 创建测试数据
        ds_repo = DataSourceRepository(db_session)
        await ds_repo.create(
            name="Config Test Source",
            protocol_type="udp",
            is_active=True,
            connection_config={"port": 8001},
        )

        ts_repo = TargetSystemRepository(db_session)
        await ts_repo.create(
            name="Config Test Target",
            protocol_type="http",
            endpoint="http://localhost:9000",
            is_active=True,
            forwarder_config={"timeout": 30},
        )

        # 加载配置
        service = ConfigurationService(db_session, redis)
        stats = await service.load_all_configs()

        assert stats["data_sources"] >= 1
        assert stats["target_systems"] >= 1

    @pytest.mark.asyncio
    async def test_get_data_source_from_cache(
        self, db_session, redis, setup_database
    ):
        """测试从缓存获取数据源配置"""
        # 创建数据源
        ds_repo = DataSourceRepository(db_session)
        ds = await ds_repo.create(
            name="Cache Test Source",
            protocol_type="mqtt",
            is_active=True,
            connection_config={"broker": "localhost"},
        )

        # 通过服务获取(会缓存)
        service = ConfigurationService(db_session, redis)
        config = await service.get_data_source(ds.id)

        assert config is not None
        assert config["name"] == "Cache Test Source"

        # 验证缓存存在
        cache_key = f"{service.CACHE_PREFIX_DATA_SOURCE}{ds.id}"
        cached = await redis.exists(cache_key)
        assert cached is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
