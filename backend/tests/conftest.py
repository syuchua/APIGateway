"""Pytest配置文件 - 提供统一的测试依赖和假数据层"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.eventbus import reset_eventbus
from app.db.database import get_db
from app.main import app


@dataclass
class InMemoryDataSource:
    id: UUID
    name: str
    description: Optional[str]
    protocol_type: str
    connection_config: Dict[str, Any]
    is_active: bool
    frame_schema_id: Optional[UUID]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    total_messages: int = 0
    last_message_at: Optional[datetime] = None


@dataclass
class InMemoryTargetSystem:
    id: UUID
    name: str
    description: Optional[str]
    protocol_type: str
    endpoint: str
    forwarder_config: Dict[str, Any]
    transform_config: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InMemoryRoutingRule:
    id: UUID
    name: str
    description: Optional[str]
    priority: int
    source_config: Dict[str, Any]
    pipeline: Dict[str, Any]
    target_systems: List[Dict[str, Any]]
    is_active: bool
    is_published: bool
    target_system_ids: List[str]
    match_count: int = 0
    last_match_at: Optional[datetime] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    logical_operator: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class InMemoryStore:
    """简易内存数据库"""

    def __init__(self):
        self.data_sources: Dict[str, InMemoryDataSource] = {}
        self.target_systems: Dict[str, InMemoryTargetSystem] = {}
        self.routing_rules: Dict[str, InMemoryRoutingRule] = {}

    def reset(self):
        self.data_sources.clear()
        self.target_systems.clear()
        self.routing_rules.clear()


class DummySession:
    """模拟的AsyncSession，提供必要的异步方法"""

    async def commit(self) -> None:  # noqa: D401
        return None

    async def rollback(self) -> None:  # noqa: D401
        return None

    async def close(self) -> None:  # noqa: D401
        return None

    async def refresh(self, _obj: Any) -> None:  # noqa: D401
        return None

    async def flush(self) -> None:  # noqa: D401
        return None


def _uuid_key(value: UUID | str) -> str:
    return str(value)


def setup_in_memory_repositories(monkeypatch: pytest.MonkeyPatch, store: InMemoryStore) -> None:
    """替换真实的Repository为内存实现"""

    class FakeDataSourceRepository:
        def __init__(self, _session):
            self.store = store

        async def create(self, **kwargs) -> InMemoryDataSource:
            ds_id = uuid4()
            instance = InMemoryDataSource(
                id=ds_id,
                name=kwargs.get("name"),
                description=kwargs.get("description"),
                protocol_type=str(kwargs.get("protocol_type", "")).upper(),
                connection_config=kwargs.get("connection_config", {}).copy(),
                is_active=kwargs.get("is_active", True),
                frame_schema_id=kwargs.get("frame_schema_id"),
            )
            self.store.data_sources[_uuid_key(ds_id)] = instance
            return instance

        async def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[InMemoryDataSource]:
            items = list(self.store.data_sources.values())
            for key, value in filters.items():
                if value is None:
                    continue
                if key == "protocol_type":
                    items = [ds for ds in items if ds.protocol_type == str(value).upper()]
                else:
                    items = [ds for ds in items if getattr(ds, key) == value]
            return items[skip : skip + limit]

        async def count(self, **filters) -> int:
            return len(await self.get_all(**filters))

        async def get(self, id: UUID) -> Optional[InMemoryDataSource]:
            return self.store.data_sources.get(_uuid_key(id))

        async def update(self, id: UUID, **kwargs) -> Optional[InMemoryDataSource]:
            ds = await self.get(id)
            if not ds:
                return None
            for key, value in kwargs.items():
                if key == "connection_config" and value is not None:
                    ds.connection_config = value.copy()
                elif hasattr(ds, key):
                    setattr(ds, key, value)
            ds.updated_at = datetime.utcnow()
            return ds

        async def delete(self, id: UUID) -> bool:
            return self.store.data_sources.pop(_uuid_key(id), None) is not None

    class FakeTargetSystemRepository:
        def __init__(self, _session):
            self.store = store

        async def create(self, **kwargs) -> InMemoryTargetSystem:
            ts_id = uuid4()
            instance = InMemoryTargetSystem(
                id=ts_id,
                name=kwargs.get("name"),
                description=kwargs.get("description"),
                protocol_type=str(kwargs.get("protocol_type", "")).lower(),
                endpoint=kwargs.get("endpoint", ""),
                forwarder_config=kwargs.get("forwarder_config", {}).copy(),
                transform_config=kwargs.get("transform_config"),
                is_active=kwargs.get("is_active", True),
            )
            self.store.target_systems[_uuid_key(ts_id)] = instance
            return instance

        async def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[InMemoryTargetSystem]:
            items = list(self.store.target_systems.values())
            for key, value in filters.items():
                if value is None:
                    continue
                items = [ts for ts in items if getattr(ts, key) == value]
            return items[skip : skip + limit]

        async def count(self, **filters) -> int:
            return len(await self.get_all(**filters))

        async def get(self, id: UUID) -> Optional[InMemoryTargetSystem]:
            return self.store.target_systems.get(_uuid_key(id))

        async def delete(self, id: UUID) -> bool:
            return self.store.target_systems.pop(_uuid_key(id), None) is not None

        async def update(self, id: UUID, **kwargs) -> Optional[InMemoryTargetSystem]:
            ts = await self.get(id)
            if not ts:
                return None
            for key, value in kwargs.items():
                if key == "forwarder_config" and value is not None:
                    ts.forwarder_config = value.copy()
                elif hasattr(ts, key):
                    setattr(ts, key, value)
            ts.updated_at = datetime.utcnow()
            return ts

    class FakeRoutingRuleRepository:
        def __init__(self, _session):
            self.store = store

        async def create(self, **kwargs) -> InMemoryRoutingRule:
            rule_id = uuid4()
            target_systems = kwargs.get("target_systems", []) or []
            target_ids = [str(ts.get("id")) for ts in target_systems if ts.get("id")]
            instance = InMemoryRoutingRule(
                id=rule_id,
                name=kwargs.get("name"),
                description=kwargs.get("description"),
                priority=kwargs.get("priority", 50),
                source_config=kwargs.get("source_config", {}).copy(),
                pipeline=kwargs.get("pipeline", {}).copy(),
                target_systems=target_systems,
                is_active=kwargs.get("is_active", True),
                is_published=kwargs.get("is_published", False),
                target_system_ids=target_ids,
                conditions=kwargs.get("conditions"),
                logical_operator=kwargs.get("logical_operator"),
            )
            self.store.routing_rules[_uuid_key(rule_id)] = instance
            return instance

        async def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[InMemoryRoutingRule]:
            items = list(self.store.routing_rules.values())
            for key, value in filters.items():
                if value is None:
                    continue
                items = [rule for rule in items if getattr(rule, key) == value]
            return items[skip : skip + limit]

        async def count(self, **filters) -> int:
            return len(await self.get_all(**filters))

        async def get(self, id: UUID) -> Optional[InMemoryRoutingRule]:
            return self.store.routing_rules.get(_uuid_key(id))

        async def update(self, id: UUID, **kwargs) -> Optional[InMemoryRoutingRule]:
            rule = await self.get(id)
            if not rule:
                return None
            for key, value in kwargs.items():
                if key == "target_systems" and value is not None:
                    rule.target_systems = value
                    rule.target_system_ids = [str(ts.get("id")) for ts in value if ts.get("id")]
                elif hasattr(rule, key):
                    setattr(rule, key, value)
            rule.updated_at = datetime.utcnow()
            return rule

        async def delete(self, id: UUID) -> bool:
            return self.store.routing_rules.pop(_uuid_key(id), None) is not None

        async def publish(self, id: UUID) -> bool:
            rule = await self.get(id)
            if not rule:
                return False
            rule.is_published = True
            rule.updated_at = datetime.utcnow()
            return True

        async def unpublish(self, id: UUID) -> bool:
            rule = await self.get(id)
            if not rule:
                return False
            rule.is_published = False
            rule.updated_at = datetime.utcnow()
            return True

        async def get_active_rules(self) -> List[InMemoryRoutingRule]:
            return sorted(
                [r for r in self.store.routing_rules.values() if r.is_active and r.is_published],
                key=lambda r: r.priority,
                reverse=True,
            )

        async def increment_match_count(self, id: UUID) -> None:
            rule = await self.get(id)
            if rule:
                rule.match_count += 1
                rule.last_match_at = datetime.utcnow()

    monkeypatch.setattr("app.api.v2.data_sources.DataSourceRepository", FakeDataSourceRepository)
    monkeypatch.setattr("app.api.v2.target_systems.TargetSystemRepository", FakeTargetSystemRepository)
    monkeypatch.setattr("app.api.v2.routing_rules.RoutingRuleRepository", FakeRoutingRuleRepository)

    # v1接口在部分测试中仍会引用
    monkeypatch.setattr("app.api.v1.data_sources.DataSourceRepository", FakeDataSourceRepository, raising=False)
    monkeypatch.setattr("app.api.v1.target_systems.TargetSystemRepository", FakeTargetSystemRepository, raising=False)
    monkeypatch.setattr("app.api.v1.routing_rules.RoutingRuleRepository", FakeRoutingRuleRepository, raising=False)


@pytest_asyncio.fixture(scope="function")
async def async_client(monkeypatch: pytest.MonkeyPatch):
    """基于内存仓库的测试客户端"""

    store = InMemoryStore()
    setup_in_memory_repositories(monkeypatch, store)

    async def override_get_db():
        yield DummySession()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def clean_eventbus():
    """测试前后重置全局 EventBus"""

    reset_eventbus()
    yield
    reset_eventbus()
