"""
完整数据流演示示例

演示场景：
1. UDP接收温度传感器数据
2. 解析固定格式数据帧（温度 + 湿度）
3. 根据温度阈值路由到不同目标系统
4. HTTP转发到目标API（使用FastAPI模拟接收服务器）

运行方式：
1. 终端1: python examples/complete_demo.py
2. 终端2: python examples/udp_sender.py (发送测试数据)
"""
import asyncio
import struct
import logging
from datetime import datetime
from uuid import uuid4
import uvicorn
from fastapi import FastAPI, Request

from app.config.logging import setup_logging
from app.core.gateway.manager import get_gateway_manager
from app.core.gateway.adapters.udp_adapter import UDPAdapterConfig
from app.schemas.frame_schema import (
    FrameSchemaResponse,
    FieldDefinition
)
from app.schemas.routing_rule import (
    RoutingRuleResponse,
    RoutingCondition,
    ConditionOperator,
    LogicalOperator
)
from app.schemas.target_system import TargetSystemResponse
from app.schemas.common import (
    ProtocolType,
    FrameType,
    DataType,
    ByteOrder,
    ChecksumType
)

# 配置日志
setup_logging("INFO")
logger = logging.getLogger(__name__)


# 创建模拟HTTP服务器
mock_app = FastAPI(title="Mock Target Systems")


@mock_app.post("/api/normal")
async def handle_normal(request: Request):
    """处理正常温度数据"""
    data = await request.json()
    logger.info(f"[正常温度API] 接收数据: {data}")
    return {
        "status": "success",
        "message": "正常温度数据已接收",
        "received_at": datetime.now().isoformat()
    }


@mock_app.post("/api/alert")
async def handle_alert(request: Request):
    """处理高温报警数据"""
    data = await request.json()
    logger.warning(f"[高温报警API] ⚠️ 收到高温报警: {data}")
    return {
        "status": "alert",
        "message": "高温报警已触发",
        "received_at": datetime.now().isoformat()
    }


async def start_mock_server():
    """在后台启动模拟HTTP服务器"""
    config = uvicorn.Config(
        mock_app,
        host="127.0.0.1",
        port=8888,
        log_level="warning"  # 降低日志级别避免干扰
    )
    server = uvicorn.Server(config)
    logger.info("模拟HTTP服务器启动在 http://localhost:8888")
    await server.serve()


async def setup_gateway():
    """配置并启动网关"""

    # 1. 获取网关管理器
    logger.info("=" * 60)
    logger.info("初始化网关管理器...")
    gateway = get_gateway_manager()

    # 2. 创建帧格式定义（温度传感器数据帧）
    logger.info("=" * 60)
    logger.info("注册帧格式定义...")
    frame_schema = FrameSchemaResponse(
        id=uuid4(),
        name="温度传感器数据帧",
        version="1.0.0",
        description="包含温度和湿度的传感器数据",
        protocol=ProtocolType.UDP,
        frame_type=FrameType.FIXED,
        total_length=8,  # 4字节温度 + 4字节湿度
        header_length=0,
        delimiter=None,
        is_active=True,
        is_published=True,
        fields=[
            FieldDefinition(
                name="temperature",
                offset=0,
                length=4,
                data_type=DataType.FLOAT32,
                byte_order=ByteOrder.LITTLE_ENDIAN,
                description="温度值（摄氏度）"
            ),
            FieldDefinition(
                name="humidity",
                offset=4,
                length=4,
                data_type=DataType.FLOAT32,
                byte_order=ByteOrder.LITTLE_ENDIAN,
                description="湿度值（百分比）"
            )
        ],
        checksum_type=ChecksumType.NONE,
        checksum_offset=None,
        checksum_length=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await gateway.register_frame_schema(frame_schema)
    logger.info(f"✓ 帧格式已注册: {frame_schema.name}")

    # 3. 创建目标系统配置
    logger.info("=" * 60)
    logger.info("注册目标系统...")

    # 正常温度数据接收系统
    normal_system_id = uuid4()
    normal_system = TargetSystemResponse(
        id=normal_system_id,
        name="正常温度数据系统",
        description="接收正常温度范围的数据",
        protocol=ProtocolType.HTTP,
        endpoint="http://localhost:8888/api/normal",
        is_active=True,
        transform_config={
            "field_mapping": {
                "parsed_data.temperature": "temp",
                "parsed_data.humidity": "hum"
            },
            "add_fields": {
                "sensor_type": "temperature",
                "status": "normal"
            }
        },
        forwarder_config={
            "url": "http://localhost:8888/api/normal",
            "method": "POST",
            "timeout": 5,
            "max_retries": 2
        },
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await gateway.register_target_system(normal_system)
    logger.info(f"✓ 目标系统已注册: {normal_system.name}")

    # 高温报警系统
    alert_system_id = uuid4()
    alert_system = TargetSystemResponse(
        id=alert_system_id,
        name="高温报警系统",
        description="接收高温报警数据",
        protocol=ProtocolType.HTTP,
        endpoint="http://localhost:8888/api/alert",
        is_active=True,
        transform_config={
            "field_mapping": {
                "parsed_data.temperature": "temp",
                "parsed_data.humidity": "hum",
                "source_address": "sensor_address"
            },
            "add_fields": {
                "alert_type": "high_temperature",
                "severity": "warning"
            }
        },
        forwarder_config={
            "url": "http://localhost:8888/api/alert",
            "method": "POST",
            "timeout": 5,
            "max_retries": 3
        },
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await gateway.register_target_system(alert_system)
    logger.info(f"✓ 目标系统已注册: {alert_system.name}")

    # 4. 创建路由规则
    logger.info("=" * 60)
    logger.info("注册路由规则...")

    # 规则1: 温度 <= 30度 -> 正常系统
    normal_rule = RoutingRuleResponse(
        id=uuid4(),
        name="正常温度路由",
        description="温度在正常范围内（≤30℃）",
        priority=5,
        is_active=True,
        is_published=True,
        logical_operator=LogicalOperator.AND,
        conditions=[
            RoutingCondition(
                field_path="parsed_data.temperature",
                operator=ConditionOperator.LESS_THAN_OR_EQUAL,
                value=30.0
            )
        ],
        target_system_ids=[normal_system_id],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await gateway.register_routing_rule(normal_rule)
    logger.info(f"✓ 路由规则已注册: {normal_rule.name}")

    # 规则2: 温度 > 30度 -> 报警系统
    alert_rule = RoutingRuleResponse(
        id=uuid4(),
        name="高温报警路由",
        description="温度超过阈值（>30℃）触发报警",
        priority=10,  # 更高优先级
        is_active=True,
        is_published=True,
        logical_operator=LogicalOperator.AND,
        conditions=[
            RoutingCondition(
                field_path="parsed_data.temperature",
                operator=ConditionOperator.GREATER_THAN,
                value=30.0
            )
        ],
        target_system_ids=[alert_system_id],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    await gateway.register_routing_rule(alert_rule)
    logger.info(f"✓ 路由规则已注册: {alert_rule.name}")

    # 5. 创建UDP适配器
    logger.info("=" * 60)
    logger.info("创建UDP适配器...")
    udp_config = UDPAdapterConfig(
        name="温度传感器UDP接收器",
        listen_address="0.0.0.0",
        listen_port=9999,
        buffer_size=8192,
        frame_schema_id=frame_schema.id,
        auto_parse=True,  # 自动解析帧数据
        is_active=True
    )
    await gateway.add_udp_adapter("sensor_udp", udp_config, frame_schema)
    logger.info(f"✓ UDP适配器已创建，监听端口: 9999")

    # 6. 启动网关
    logger.info("=" * 60)
    logger.info("启动网关...")
    await gateway.start()
    logger.info("✓ 网关启动成功!")

    # 7. 打印配置摘要
    logger.info("=" * 60)
    logger.info("【配置摘要】")
    logger.info(f"  UDP监听端口: 9999")
    logger.info(f"  帧格式: {frame_schema.name}")
    logger.info(f"  路由规则:")
    logger.info(f"    - 温度 ≤ 30℃ -> 正常系统 (http://localhost:8888/api/normal)")
    logger.info(f"    - 温度 > 30℃ -> 报警系统 (http://localhost:8888/api/alert)")
    logger.info("=" * 60)
    logger.info("")
    logger.info("🚀 系统已就绪！")
    logger.info("")
    logger.info("📡 发送测试数据:")
    logger.info("   在另一个终端运行: python examples/udp_sender.py")
    logger.info("")
    logger.info("   或使用以下命令发送数据:")
    logger.info("   python -c \"import socket, struct; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(struct.pack('<ff', 25.5, 60.0), ('127.0.0.1', 9999))\"")
    logger.info("")
    logger.info("按 Ctrl+C 停止系统")
    logger.info("=" * 60)

    return gateway


async def main():
    """主函数"""

    # 启动模拟HTTP服务器（后台运行）
    logger.info("=" * 60)
    logger.info("启动模拟HTTP服务器...")
    mock_server_task = asyncio.create_task(start_mock_server())

    # 等待服务器启动
    await asyncio.sleep(2)

    # 配置并启动网关
    gateway = await setup_gateway()

    try:
        # 保持运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n接收到停止信号...")

    # 清理资源
    logger.info("停止网关...")
    await gateway.stop()

    # 取消模拟服务器
    mock_server_task.cancel()
    try:
        await mock_server_task
    except asyncio.CancelledError:
        pass

    logger.info("系统已停止")


if __name__ == "__main__":
    asyncio.run(main())
