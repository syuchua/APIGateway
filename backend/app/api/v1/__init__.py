"""
API v1路由模块
"""
from .data_sources import router as data_sources_router
from .target_systems import router as target_systems_router
from .routing_rules import router as routing_rules_router
from .frame_schemas import router as frame_schemas_router
from .stats import router as stats_router
from .monitor import router as monitor_router
from .encryption_keys import router as encryption_keys_router
from .auth import router as auth_router

__all__ = [
    "data_sources_router",
    "target_systems_router",
    "routing_rules_router",
    "frame_schemas_router",
    "stats_router",
    "monitor_router",
    "encryption_keys_router",
    "auth_router",
]
