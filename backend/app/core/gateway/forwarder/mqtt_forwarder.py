"""
MQTT转发器实现
支持MQTT协议的数据转发功能
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    MQTT_AVAILABLE = False

from app.core.gateway.forwarder.base import BaseForwarder
from app.schemas.forwarder import (
    MQTTForwarderConfig,
    ForwardResult,
    ForwardStatus
)

logger = logging.getLogger(__name__)


class MQTTForwarder(BaseForwarder):
    """MQTT转发器"""
    
    def __init__(self, config: MQTTForwarderConfig):
        super().__init__(config)
        self.config: MQTTForwarderConfig = config
        self.client: Optional[Any] = None
        self.is_connected = False
        self._connecting = False  # 防止重复连接
        
        logger.info(f"初始化MQTT转发器: {config.host}:{config.port}, topic: {config.topic}")
    
    async def _connect(self) -> bool:
        """建立MQTT连接"""
        if self._connecting:
            # 如果正在连接，等待连接完成（最多等待timeout时间）
            wait_start = time.time()
            while self._connecting and (time.time() - wait_start) < self.config.timeout:
                await asyncio.sleep(0.1)
            return self.is_connected

        self._connecting = True
        
        try:
            if not MQTT_AVAILABLE:
                logger.error("paho-mqtt库未安装，无法使用MQTT转发器")
                return False
                
            if self.is_connected and self.client:
                # 检查连接是否仍然有效
                if hasattr(self.client, 'is_connected') and self.client.is_connected():
                    return True
                else:
                    await self._disconnect()
            
            # 创建MQTT客户端
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            
            # 设置认证信息
            if self.config.username:
                self.client.username_pw_set(
                    self.config.username,
                    self.config.password
                )
            
            # 设置TLS
            if self.config.tls_enabled:
                self.client.tls_set(
                    ca_certs=self.config.ca_cert,
                    certfile=self.config.cert_file,
                    keyfile=self.config.key_file
                )
            
            # 设置回调函数
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            
            # 连接到MQTT代理
            result = self.client.connect(
                self.config.host,
                self.config.port,
                self.config.keepalive
            )

            if result != 0:
                logger.error(f"MQTT连接失败，错误码: {result}")
                self.client = None
                self._connecting = False
                return False

            # 启动网络循环
            self.client.loop_start()

            # 手动调用连接回调（测试时需要）
            if hasattr(self.client, '_trigger_on_connect'):
                self._on_connect(self.client, None, None, 0)

            # 等待连接建立（通过_on_connect回调设置is_connected）
            timeout = self.config.timeout
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)

            if not self.is_connected:
                logger.error("MQTT连接超时")
                await self._disconnect()
                self._connecting = False
                return False
            
            logger.info(f"MQTT连接建立成功: {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            self.is_connected = False
            self.client = None
            return False
        finally:
            self._connecting = False
    
    async def _disconnect(self):
        """断开MQTT连接"""
        try:
            if self.client:
                if hasattr(self.client, 'loop_stop'):
                    self.client.loop_stop()
                if hasattr(self.client, 'disconnect'):
                    self.client.disconnect()
                self.client = None
            
            self.is_connected = False
            logger.info("MQTT连接已断开")
            
        except Exception as e:
            logger.error(f"断开MQTT连接时出错: {e}")
            self.is_connected = False
            self.client = None
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT连接成功")
        else:
            self.is_connected = False
            logger.error(f"MQTT连接失败，错误码: {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT意外断开连接，错误码: {rc}")
        else:
            logger.info("MQTT连接正常断开")

    def _on_publish(self, client, userdata, mid, rc=0, properties=None):
        """发布回调"""
        logger.info(f"MQTT消息发布成功，消息ID: {mid}")
    
    def _resolve_topic(self, data: Dict[str, Any]) -> str:
        topic = self.config.topic or ""
        if "{" in topic and "}" in topic:
            replacements = {
                "source_id": data.get("data_source_id") or data.get("source_id"),
                "source_name": data.get("source_name") or data.get("adapter_name"),
                "protocol": getattr(data.get("source_protocol"), "value", None) or data.get("source_protocol"),
                "target_id": data.get("target_id"),
                "message_id": data.get("message_id"),
            }
            for key, value in replacements.items():
                if value is None:
                    continue
                topic = topic.replace(f"{{{key}}}", str(value))
            # 未替换的占位符直接移除花括号，避免broker报错
            topic = topic.replace("{", "").replace("}", "")
        return topic or self.config.topic

    async def _send_data(self, data: Dict[str, Any]) -> ForwardResult:
        """发送数据到MQTT代理"""
        start_time = time.time()

        try:
            # 序列化数据
            json_data = json.dumps(data, ensure_ascii=False)

            topic = self._resolve_topic(data)

            # 发布消息
            result = self.client.publish(
                topic,
                json_data,
                qos=self.config.qos
            )

            if hasattr(result, 'rc') and result.rc != 0:
                raise Exception(f"MQTT发布失败，错误码: {result.rc}")
            
            duration = time.time() - start_time
            
            return ForwardResult(
                status=ForwardStatus.SUCCESS,
                status_code=None,
                response_text=None,
                error=None,
                retry_count=0,
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"发送MQTT数据失败: {e}"
            logger.error(error_msg)
            
            # 连接出错时断开连接
            await self._disconnect()
            
            return ForwardResult(
                status=ForwardStatus.FAILED,
                status_code=None,
                response_text=None,
                error=error_msg,
                retry_count=0,
                duration=duration
            )
    
    async def forward(self, data: Dict[str, Any]) -> ForwardResult:
        """转发数据"""
        self._stats["forwards_attempted"] += 1
        
        last_error = None
        actual_retry_count = 0
        
        for attempt in range(self.config.retry_times + 1):
            try:
                # 建立连接（如果尚未连接）
                if not await self._connect():
                    raise Exception("Failed to establish MQTT connection")
                
                # 发送数据
                result = await self._send_data(data)
                
                if result.status == ForwardStatus.SUCCESS:
                    self._stats["forwards_succeeded"] += 1
                    # 更新重试次数
                    result.retry_count = actual_retry_count
                    return result
                else:
                    last_error = result.error
                    actual_retry_count += 1
                    if attempt < self.config.retry_times:
                        logger.warning(f"MQTT转发失败，准备重试 ({attempt + 1}/{self.config.retry_times}): {last_error}")
                        await asyncio.sleep(self.config.retry_delay)
                        await self._disconnect()  # 重试前断开连接
            
            except Exception as e:
                last_error = str(e)
                actual_retry_count += 1
                if attempt < self.config.retry_times:
                    logger.warning(f"MQTT转发异常，准备重试 ({attempt + 1}/{self.config.retry_times}): {last_error}")
                    await asyncio.sleep(self.config.retry_delay)
                    await self._disconnect()  # 重试前断开连接
        
        # 所有重试都失败了
        self._stats["forwards_failed"] += 1
        
        return ForwardResult(
            status=ForwardStatus.FAILED,
            status_code=None,
            response_text=None,
            error=last_error or "Unknown error",
            retry_count=min(actual_retry_count, self.config.retry_times),
            duration=0.0
        )
    
    async def forward_batch(self, data_list: List[Dict[str, Any]]) -> List[ForwardResult]:
        """批量转发数据"""
        results = []
        
        for data in data_list:
            result = await self.forward(data)
            results.append(result)
        
        return results
    
    async def close(self):
        """关闭转发器"""
        try:
            await self._disconnect()
            logger.info("MQTT转发器已关闭")
        except Exception as e:
            logger.error(f"关闭MQTT转发器时出错: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = super().get_stats()
        stats.update({
            "protocol": "mqtt",
            "target": f"{self.config.host}:{self.config.port}",
            "topic": self.config.topic,
            "qos": self.config.qos,
            "is_connected": self.is_connected
        })
        return stats
