# 工厂模式架构设计

## 概述

使用工厂模式统一管理协议适配器和转发器的创建，提高代码的可维护性、可扩展性和规范性。

## 核心优势

### 1. **解耦创建逻辑**
- 客户端代码无需知道具体实现类
- 新增协议只需实现接口，注册到工厂即可

### 2. **统一接口**
- 所有适配器/转发器遵循相同的基类接口
- 便于多态调用和单元测试

### 3. **配置驱动**
- 通过配置文件动态创建实例
- 运行时可扩展，无需修改代码

### 4. **类型安全**
- 使用枚举和类型注解
- 编译时捕获错误

## 架构设计

### 一、协议适配器工厂

```
┌─────────────────────────────────────────┐
│        AdapterFactory (工厂)            │
│  ┌───────────────────────────────────┐  │
│  │  register(protocol, adapter_cls)  │  │
│  │  create(protocol, config)         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  │
                  ├─────────────────┬─────────────────┬──────────────
                  ▼                 ▼                 ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │ UDPAdapter   │  │ HTTPAdapter  │  │  WSAdapter   │
          │ (具体实现)    │  │ (具体实现)    │  │ (具体实现)    │
          └──────────────┘  └──────────────┘  └──────────────┘
                  ▲                 ▲                 ▲
                  └─────────────────┴─────────────────┘
                            │
                    ┌───────────────┐
                    │ BaseAdapter   │
                    │   (抽象基类)   │
                    │ - start()     │
                    │ - stop()      │
                    │ - get_stats() │
                    └───────────────┘
```

### 二、转发器工厂

```
┌─────────────────────────────────────────┐
│      ForwarderFactory (工厂)            │
│  ┌───────────────────────────────────┐  │
│  │  register(protocol, forwarder_cls)│  │
│  │  create(protocol, config)         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  │
                  ├─────────────────┬─────────────────┬──────────────
                  ▼                 ▼                 ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │HTTPForwarder   │ │  WSForwarder   │ │ UDPForwarder   │
        │ (具体实现)      │ │ (具体实现)      │ │ (具体实现)      │
        └────────────────┘ └────────────────┘ └────────────────┘
                  ▲                 ▲                 ▲
                  └─────────────────┴─────────────────┘
                            │
                    ┌───────────────┐
                    │ BaseForwarder │
                    │  (抽象基类)    │
                    │ - forward()   │
                    │ - close()     │
                    └───────────────┘
```

## 实现方案

### 1. BaseAdapter 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

class BaseAdapter(ABC):
    """协议适配器基类"""

    def __init__(self, config: Dict[str, Any], eventbus: SimpleEventBus):
        self.config = config
        self.eventbus = eventbus
        self.is_running = False

    @abstractmethod
    async def start(self):
        """启动适配器"""
        pass

    @abstractmethod
    async def stop(self):
        """停止适配器"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass

    def _publish_message(self, raw_data: bytes, source_info: Dict):
        """发布消息到EventBus（通用方法）"""
        # 统一的消息发布逻辑
        pass
```

### 2. AdapterFactory 工厂类

```python
from typing import Dict, Type
from app.schemas.common import ProtocolType

class AdapterFactory:
    """协议适配器工厂"""

    _adapters: Dict[ProtocolType, Type[BaseAdapter]] = {}

    @classmethod
    def register(cls, protocol: ProtocolType, adapter_class: Type[BaseAdapter]):
        """注册适配器类型"""
        cls._adapters[protocol] = adapter_class

    @classmethod
    def create(cls, protocol: ProtocolType, config: Dict, eventbus: SimpleEventBus) -> BaseAdapter:
        """创建适配器实例"""
        adapter_class = cls._adapters.get(protocol)
        if not adapter_class:
            raise ValueError(f"不支持的协议类型: {protocol}")

        return adapter_class(config, eventbus)

    @classmethod
    def get_supported_protocols(cls) -> List[ProtocolType]:
        """获取支持的协议列表"""
        return list(cls._adapters.keys())

# 注册具体实现
AdapterFactory.register(ProtocolType.UDP, UDPAdapter)
AdapterFactory.register(ProtocolType.HTTP, HTTPAdapter)
AdapterFactory.register(ProtocolType.WEBSOCKET, WebSocketAdapter)
```

### 3. BaseForwarder 抽象基类

```python
from abc import ABC, abstractmethod

class BaseForwarder(ABC):
    """转发器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def forward(self, data: Dict[str, Any]) -> ForwardResult:
        """转发数据"""
        pass

    @abstractmethod
    async def forward_batch(self, data_list: List[Dict]) -> List[ForwardResult]:
        """批量转发"""
        pass

    @abstractmethod
    async def close(self):
        """关闭连接，释放资源"""
        pass
```

### 4. ForwarderFactory 工厂类

```python
class ForwarderFactory:
    """转发器工厂"""

    _forwarders: Dict[ProtocolType, Type[BaseForwarder]] = {}

    @classmethod
    def register(cls, protocol: ProtocolType, forwarder_class: Type[BaseForwarder]):
        """注册转发器类型"""
        cls._forwarders[protocol] = forwarder_class

    @classmethod
    def create(cls, protocol: ProtocolType, config: Dict) -> BaseForwarder:
        """创建转发器实例"""
        forwarder_class = cls._forwarders.get(protocol)
        if not forwarder_class:
            raise ValueError(f"不支持的协议类型: {protocol}")

        return forwarder_class(config)

# 注册具体实现
ForwarderFactory.register(ProtocolType.HTTP, HTTPForwarder)
ForwarderFactory.register(ProtocolType.WEBSOCKET, WebSocketForwarder)
ForwarderFactory.register(ProtocolType.UDP, UDPForwarder)
```

## 使用示例

### 创建适配器

```python
# 方式1：直接使用工厂
adapter = AdapterFactory.create(
    protocol=ProtocolType.UDP,
    config=udp_config,
    eventbus=eventbus
)
await adapter.start()

# 方式2：从配置文件创建
data_source_config = {
    "protocol": "UDP",
    "listen_port": 9999,
    "auto_parse": True
}

adapter = AdapterFactory.create(
    protocol=ProtocolType[data_source_config["protocol"]],
    config=data_source_config,
    eventbus=eventbus
)
```

### 创建转发器

```python
# 从目标系统配置创建
target_system = TargetSystemResponse(
    protocol=ProtocolType.HTTP,
    forwarder_config={
        "url": "http://api.example.com",
        "method": "POST"
    }
)

forwarder = ForwarderFactory.create(
    protocol=target_system.protocol,
    config=target_system.forwarder_config
)

result = await forwarder.forward(data)
```

## 重构步骤

### 阶段1：创建基类和工厂 ✅
1. [x] 创建 `BaseAdapter` 抽象基类
2. [x] 创建 `AdapterFactory` 工厂类
3. [x] 创建 `BaseForwarder` 抽象基类
4. [x] 创建 `ForwarderFactory` 工厂类

### 阶段2：重构现有实现
1. [ ] 重构 `UDPAdapter` 继承 `BaseAdapter`
2. [ ] 重构 `HTTPForwarder` 继承 `BaseForwarder`
3. [ ] 注册到对应工厂

### 阶段3：实现新协议
1. [ ] 实现 `HTTPAdapter` (继承 `BaseAdapter`)
2. [ ] 实现 `WebSocketAdapter` (继承 `BaseAdapter`)
3. [ ] 实现 `TCPAdapter` (继承 `BaseAdapter`)
4. [ ] 实现 `WebSocketForwarder` (继承 `BaseForwarder`)
5. [ ] 实现 `UDPForwarder` (继承 `BaseForwarder`)

### 阶段4：集成到网关管理器
1. [ ] 更新 `GatewayManager` 使用工厂创建适配器
2. [ ] 更新 `ForwarderManager` 使用工厂创建转发器
3. [ ] 更新测试用例

## 设计模式对比

### 当前实现（无工厂）
```python
# ❌ 问题：紧耦合，难以扩展
if protocol == ProtocolType.UDP:
    adapter = UDPAdapter(config, eventbus)
elif protocol == ProtocolType.HTTP:
    adapter = HTTPAdapter(config, eventbus)
elif protocol == ProtocolType.WEBSOCKET:
    adapter = WebSocketAdapter(config, eventbus)
# 每增加一个协议都要修改这段代码
```

### 工厂模式实现
```python
# ✅ 优点：解耦，易于扩展
adapter = AdapterFactory.create(protocol, config, eventbus)
# 新增协议只需实现类并注册到工厂，无需修改客户端代码
```

## 总结

使用工厂模式的优势：

1. **开闭原则** - 对扩展开放，对修改关闭
2. **单一职责** - 创建逻辑与业务逻辑分离
3. **依赖倒置** - 依赖抽象而非具体实现
4. **便于测试** - 可轻松mock和替换实现
5. **配置驱动** - 支持动态创建和热加载

这个设计将使系统更加健壮、可维护和可扩展！
