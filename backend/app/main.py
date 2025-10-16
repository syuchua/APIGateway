"""
FastAPI应用主入口
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.config.logging import setup_logging
from app.core.gateway.manager import get_gateway_manager
from app.core.eventbus import get_eventbus
from app.db.database import close_db
from app.db.redis import redis_client
from app.services.user_service import ensure_default_admin_user

# 导入API路由
from app.api import api_router, api_v2_router_export
from app.api.websocket import (
    websocket_monitor_endpoint,
    websocket_logs_endpoint,
    websocket_messages_endpoint,
    websocket_data_source_endpoint,
)

# 配置日志
settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("应用启动中...")

    # 连接Redis
    await redis_client.connect()
    logger.info("Redis连接成功")

    # 获取网关管理器
    gateway_manager = get_gateway_manager()
    eventbus = get_eventbus()

    logger.info(f"EventBus初始化完成")
    logger.info(f"网关管理器初始化完成")

    # 确保默认管理员存在
    try:
        await ensure_default_admin_user()
    except Exception:  # pragma: no cover - 启动日志记录
        logger.exception("初始化默认管理员账户失败")
        raise

    # 这里可以在启动时加载配置、启动适配器等
    # 但为了演示,我们在示例脚本中手动配置

    yield

    # 关闭时
    logger.info("应用关闭中...")
    if gateway_manager.is_running:
        await gateway_manager.stop()

    # 关闭数据库连接
    await close_db()
    await redis_client.close()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    gateway_manager = get_gateway_manager()
    status = gateway_manager.get_status()

    return {
        "status": "healthy" if gateway_manager.is_running else "stopped",
        "gateway": status
    }


@app.get("/status")
async def get_status():
    """获取网关状态"""
    gateway_manager = get_gateway_manager()
    return gateway_manager.get_status()


# 注册API路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_v2_router_export, prefix="/api")

# 注册WebSocket端点
app.websocket("/ws/monitor")(websocket_monitor_endpoint)
app.websocket("/ws/logs")(websocket_logs_endpoint)
app.websocket("/ws/messages")(websocket_messages_endpoint)
app.websocket("/ws/data-sources/{data_source_id}")(websocket_data_source_endpoint)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
