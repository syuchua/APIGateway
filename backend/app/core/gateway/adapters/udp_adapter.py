"""
UDP协议适配器实现
基于asyncio的高性能UDP服务器，接收UDP数据并发布到EventBus
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from app.core.eventbus import SimpleEventBus, TopicCategory
from app.schemas.common import ProtocolType
from app.schemas.frame_schema import FrameSchemaResponse
from app.core.gateway.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class UDPAdapterConfig(BaseModel):
    """UDP适配器配置模型"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, description="适配器名称")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    listen_address: str = Field(default="0.0.0.0", description="监听地址")
    listen_port: int = Field(..., ge=0, le=65535, description="监听端口，0表示自动分配")
    buffer_size: int = Field(default=8192, ge=512, description="接收缓冲区大小")
    frame_schema_id: Optional[UUID] = Field(None, description="帧格式ID")
    auto_parse: bool = Field(default=False, description="是否自动解析数据帧")
    is_active: bool = Field(default=True, description="是否激活")


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP协议处理器"""

    def __init__(self, adapter: 'UDPAdapter'):
        self.adapter = adapter
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        """连接建立时调用"""
        self.transport = transport
        sock = transport.get_extra_info('socket')
        if sock:
            # 获取实际绑定的端口
            self.adapter.actual_port = sock.getsockname()[1]

        logger.info(
            f"UDP适配器 '{self.adapter.udp_config.name}' 启动成功，"
            f"监听 {self.adapter.udp_config.listen_address}:{self.adapter.actual_port}"
        )

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """接收到数据报时调用"""
        try:
            # 记录接收到的数据
            source_address, source_port = addr

            # 构建消息数据
            message_data = {
                "message_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "source_protocol": ProtocolType.UDP,
                "data_source_id": self.adapter.udp_config.data_source_id,
                "source_address": source_address,
                "source_port": source_port,
                "raw_data": data,
                "data_size": len(data),
                "adapter_name": self.adapter.udp_config.name
            }

            # 如果配置了帧格式且需要自动解析
            if self.adapter.udp_config.auto_parse and self.adapter.frame_parser:
                try:
                    parsed_data = self.adapter.frame_parser.parse(data)
                    message_data["parsed_data"] = parsed_data

                    # 发布到解析成功主题
                    self.adapter.eventbus.publish(
                        topic=TopicCategory.DATA_PARSED,
                        data=message_data,
                        source="udp_adapter"
                    )

                    logger.info(f"UDP数据解析成功: {parsed_data}")
                except Exception as parse_error:
                    # 解析失败，记录错误但仍发布原始数据
                    message_data["parse_error"] = str(parse_error)
                    logger.warning(f"UDP数据解析失败: {parse_error}")

            # 发布到EventBus
            self.adapter.eventbus.publish(
                topic=TopicCategory.UDP_RECEIVED,
                data=message_data,
                source="udp_adapter"
            )

            logger.info(
                f"UDP接收数据: {len(data)} bytes from {source_address}:{source_port}"
            )

        except Exception as e:
            logger.error(f"处理UDP数据时出错: {e}", exc_info=True)

    def error_received(self, exc: Exception):
        """接收到错误时调用"""
        logger.error(f"UDP协议错误: {exc}")

    def connection_lost(self, exc: Optional[Exception]):
        """连接丢失时调用"""
        if exc:
            logger.error(f"UDP连接丢失: {exc}")
        else:
            logger.info(f"UDP适配器 '{self.adapter.udp_config.name}' 已停止")


class UDPAdapter(BaseAdapter):
    """
    UDP协议适配器

    功能：
    - 异步接收UDP数据包
    - 解析数据帧（可选）
    - 发布到EventBus
    - 支持高并发处理
    """

    def __init__(
        self,
        config: Dict[str, Any],
        eventbus: SimpleEventBus,
        frame_schema: Optional[FrameSchemaResponse] = None
    ):
        """
        初始化UDP适配器

        Args:
            config: 适配器配置字典（兼容UDPAdapterConfig）
            eventbus: EventBus实例
            frame_schema: 帧格式定义（可选）
        """
        # 调用父类初始化
        super().__init__(config, eventbus, frame_schema)

        # 如果config是字典，转换为UDPAdapterConfig
        if isinstance(config, dict):
            self.udp_config = UDPAdapterConfig(**config)
        elif isinstance(config, UDPAdapterConfig):
            self.udp_config = config
        else:
            raise TypeError("config must be dict or UDPAdapterConfig")

        # UDP特定属性
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[UDPProtocol] = None
        self.actual_port = 0  # 实际监听的端口
        self.frame_parser = None

        # 如果提供了帧格式定义，创建解析器
        if frame_schema:
            from app.core.gateway.frame.parser import FrameParser
            self.frame_parser = FrameParser(frame_schema)

    async def start(self):
        """启动UDP适配器"""
        if self.is_running:
            raise RuntimeError(f"UDP适配器 '{self.udp_config.name}' already running")

        try:
            # 获取事件循环
            loop = asyncio.get_event_loop()

            # 创建UDP endpoint
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                lambda: UDPProtocol(self),
                local_addr=(self.udp_config.listen_address, self.udp_config.listen_port)
            )

            self.is_running = True

            logger.info(
                f"UDP适配器 '{self.udp_config.name}' 启动，"
                f"监听 {self.udp_config.listen_address}:{self.actual_port}"
            )

        except Exception as e:
            logger.error(f"启动UDP适配器失败: {e}", exc_info=True)
            raise

    async def stop(self):
        """停止UDP适配器"""
        if not self.is_running:
            return

        try:
            if self.transport:
                self.transport.close()
                self.transport = None

            self.protocol = None
            self.is_running = False
            self.actual_port = 0

            logger.info(f"UDP适配器 '{self.udp_config.name}' 已停止")

        except Exception as e:
            logger.error(f"停止UDP适配器失败: {e}", exc_info=True)
            raise

    async def restart(self):
        """重启UDP适配器"""
        await self.stop()
        await asyncio.sleep(0.1)  # 短暂等待，确保端口释放
        await self.start()

    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        return {
            "name": self.udp_config.name,
            "is_running": self.is_running,
            "listen_address": self.udp_config.listen_address,
            "listen_port": self.udp_config.listen_port,
            "actual_port": self.actual_port,
            "buffer_size": self.udp_config.buffer_size,
            "auto_parse": self.udp_config.auto_parse,
            "has_frame_parser": self.frame_parser is not None,
            **self._stats  # 包含父类统计信息
        }


# 便捷函数
async def create_udp_adapter(
    name: str,
    listen_port: int,
    eventbus: SimpleEventBus,
    listen_address: str = "0.0.0.0",
    buffer_size: int = 8192
) -> UDPAdapter:
    """
    创建并启动UDP适配器

    Args:
        name: 适配器名称
        listen_port: 监听端口
        eventbus: EventBus实例
        listen_address: 监听地址
        buffer_size: 缓冲区大小

    Returns:
        UDPAdapter: 已启动的UDP适配器实例
    """
    config = UDPAdapterConfig(
        name=name,
        listen_address=listen_address,
        listen_port=listen_port,
        buffer_size=buffer_size
    )

    adapter = UDPAdapter(config, eventbus)
    await adapter.start()

    return adapter


if __name__ == "__main__":
    # 简单测试示例
    async def main():
        from app.core.eventbus import get_eventbus

        # 创建EventBus
        eventbus = get_eventbus()

        # 订阅UDP接收消息
        def on_udp_received(data, topic, source):
            print(f"接收到UDP消息: {data['data_size']} bytes")
            print(f"来源: {data['source_address']}:{data['source_port']}")
            print(f"数据: {data['raw_data'][:50]}")  # 只打印前50字节

        eventbus.subscribe(TopicCategory.UDP_RECEIVED, on_udp_received)

        # 创建UDP适配器
        adapter = await create_udp_adapter(
            name="测试UDP适配器",
            listen_port=8888,
            eventbus=eventbus
        )

        print(f"UDP适配器运行在端口 {adapter.actual_port}")
        print("发送UDP数据到 127.0.0.1:8888 进行测试...")
        print("按Ctrl+C停止")

        try:
            # 保持运行
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n停止适配器...")
            await adapter.stop()

    # 运行
    asyncio.run(main())
