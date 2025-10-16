"""
API路由主入口
"""
from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_active_user
from app.api.v1 import auth, data_sources, target_systems, routing_rules, frame_schemas, stats, monitor, encryption_keys
from app.api.v2 import api_v2_router

api_router = APIRouter()

# 认证模块
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"],
)

# 注册v1模块路由（保持向后兼容）
api_router.include_router(
    data_sources.router,
    prefix="/data-sources",
    tags=["数据源管理-v1"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    target_systems.router,
    prefix="/target-systems",
    tags=["目标系统管理-v1"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    routing_rules.router,
    prefix="/routing-rules",
    tags=["路由规则管理-v1"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    frame_schemas.router,
    prefix="/frame-schemas",
    tags=["帧格式管理"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    stats.router,
    prefix="/stats",
    tags=["统计监控"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    monitor.router,
    prefix="/monitor",
    tags=["系统监控"],
    dependencies=[Depends(get_current_active_user)],
)

api_router.include_router(
    encryption_keys.router,
    prefix="/encryption-keys",
    tags=["密钥管理"],
    dependencies=[Depends(get_current_active_user)],
)

# v2 API路由
api_v2_router_export = APIRouter()
api_v2_router_export.include_router(
    api_v2_router,
    prefix="/v2",
    tags=["API-v2"],
    dependencies=[Depends(get_current_active_user)],
)

__all__ = ["api_router", "api_v2_router_export"]
