"""
API v2路由模块
使用新的嵌套Schema和统一ApiResponse格式
"""
from fastapi import APIRouter

from .data_sources import router as data_sources_router
from .target_systems import router as target_systems_router
from .routing_rules import router as routing_rules_router
from .frame_schemas import router as frame_schemas_router

# 创建v2 API路由器
api_v2_router = APIRouter()

# 注册子路由
api_v2_router.include_router(
    data_sources_router,
    prefix="/data-sources",
    tags=["data-sources-v2"]
)

api_v2_router.include_router(
    target_systems_router,
    prefix="/target-systems",
    tags=["target-systems-v2"]
)

api_v2_router.include_router(
    routing_rules_router,
    prefix="/routing-rules",
    tags=["routing-rules-v2"]
)

api_v2_router.include_router(
    frame_schemas_router,
    prefix="/frame-schemas",
    tags=["frame-schemas-v2"]
)

__all__ = ["api_v2_router"]
