# 完整示例运行指南

## 功能说明

本示例演示了完整的数据流处理：

```
UDP接收数据 → 帧解析 → 路由判断 → 数据转换 → HTTP转发
```

### 业务场景

温度传感器通过UDP发送数据（温度+湿度），网关根据温度值进行智能路由：
- **温度 ≤ 30℃**: 发送到正常数据系统
- **温度 > 30℃**: 触发高温报警系统

## 运行步骤

### 1. 安装依赖

```bash
cd backend
uv pip install aiohttp  # 用于模拟HTTP服务器
```

### 2. 启动完整示例

在终端1中运行:

```bash
cd backend
python examples/complete_demo.py
```

你将看到系统初始化日志，包括:
- ✓ 帧格式注册
- ✓ 目标系统注册
- ✓ 路由规则注册
- ✓ UDP适配器创建
- ✓ 网关启动成功

### 3. 发送测试数据

**方式1: 使用测试脚本（推荐）**

在终端2中运行:

```bash
cd backend
python examples/udp_sender.py
```

该脚本会发送多组测试数据，包括:
- 正常温度数据（18-28℃）
- 高温报警数据（31-40℃）
- 临界值测试（30℃, 30.1℃）

**方式2: 使用命令行**

```bash
# 发送正常温度数据 (25.5℃, 60%湿度)
python -c "import socket, struct; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(struct.pack('<ff', 25.5, 60.0), ('127.0.0.1', 9999))"

# 发送高温数据 (35℃, 65%湿度)
python -c "import socket, struct; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(struct.pack('<ff', 35.0, 65.0), ('127.0.0.1', 9999))"
```

## 预期输出

### 网关端 (终端1)

当接收到数据时，你会看到:

```
[INFO] UDP接收数据: 8 bytes from 127.0.0.1:xxxxx
[INFO] UDP数据解析成功: {'temperature': 25.5, 'humidity': 60.0}
[INFO] 路由消息: 1 个规则匹配, 1 个目标系统
[INFO] [正常温度API] 接收数据: {'temp': 25.5, 'hum': 60.0, 'sensor_type': 'temperature', 'status': 'normal'}
```

当温度超过30℃时:

```
[WARNING] [高温报警API] ⚠️ 收到高温报警: {'temp': 35.0, 'hum': 65.0, 'alert_type': 'high_temperature', 'severity': 'warning', 'sensor_address': '127.0.0.1'}
```

### 发送端 (终端2)

```
【场景1】发送正常温度数据（应该路由到正常系统）
[HH:MM:SS] 发送数据: 温度=25.3℃, 湿度=62.1%
[HH:MM:SS] 发送数据: 温度=22.8℃, 湿度=55.4%

【场景2】发送高温数据（应该触发报警系统）
[HH:MM:SS] 发送数据: 温度=35.2℃, 湿度=58.9%
[HH:MM:SS] 发送数据: 温度=38.1℃, 湿度=45.3%
```

## 数据流详解

### 1. UDP接收阶段

UDP适配器监听端口9999，接收8字节数据包:
```
Offset 0-3: 温度 (float32, 小端序)
Offset 4-7: 湿度 (float32, 小端序)
```

### 2. 帧解析阶段

根据注册的帧格式，将原始字节解析为:
```json
{
  "temperature": 25.5,
  "humidity": 60.0
}
```

### 3. 路由判断阶段

路由引擎评估两条规则:
- **规则1** (优先级5): `temperature <= 30` → 正常系统
- **规则2** (优先级10): `temperature > 30` → 报警系统

### 4. 数据转换阶段

根据目标系统的转换配置:
```json
{
  "temp": 25.5,           // 字段映射: parsed_data.temperature -> temp
  "hum": 60.0,            // 字段映射: parsed_data.humidity -> hum
  "sensor_type": "temperature",  // 新增字段
  "status": "normal"      // 新增字段
}
```

### 5. HTTP转发阶段

使用HTTP POST将数据发送到目标API:
- 正常系统: `POST http://localhost:8888/api/normal`
- 报警系统: `POST http://localhost:8888/api/alert`

## 停止系统

在运行示例的终端中按 `Ctrl+C` 停止系统。

系统会优雅关闭：
- 停止UDP适配器
- 停止数据处理管道
- 关闭HTTP模拟服务器

## 查看系统状态

启动FastAPI应用后，可以访问:

```bash
# 启动FastAPI (可选，示例已包含完整功能)
python -m app.main

# 查看健康状态
curl http://localhost:8000/health

# 查看网关状态
curl http://localhost:8000/status
```

## 故障排查

### 问题1: 端口被占用

```
OSError: [Errno 48] Address already in use
```

**解决方法**: 修改端口号
- UDP端口: 在`complete_demo.py`中修改`listen_port`
- HTTP端口: 修改`mock_http_server`的`port`参数

### 问题2: 没有看到日志输出

**检查事项**:
1. 确认UDP端口是否正确 (默认9999)
2. 检查防火墙设置
3. 确认数据格式是否正确 (2个float32, 小端序)

### 问题3: 数据未转发

**检查事项**:
1. 确认路由规则是否匹配
2. 检查目标系统配置是否正确
3. 查看日志中的错误信息

## 扩展示例

### 修改路由规则

编辑`complete_demo.py`，修改路由条件:

```python
# 例如: 温度 > 35℃ 且 湿度 < 50% 才报警
conditions=[
    RoutingCondition(
        field_path="parsed_data.temperature",
        operator=ConditionOperator.GREATER_THAN,
        value=35.0
    ),
    RoutingCondition(
        field_path="parsed_data.humidity",
        operator=ConditionOperator.LESS_THAN,
        value=50.0
    )
]
```

### 添加更多目标系统

```python
# 添加日志系统
log_system = TargetSystemResponse(
    id=uuid4(),
    name="日志记录系统",
    protocol=ProtocolType.HTTP,
    endpoint="http://localhost:8888/api/log",
    # ... 其他配置
)
await gateway.register_target_system(log_system)
```

## 总结

通过这个示例，你可以看到:
✅ EventBus的高性能消息传递
✅ UDP协议的异步接收和处理
✅ 灵活的帧格式解析
✅ 强大的路由规则引擎
✅ 数据转换和HTTP转发
✅ 完整的数据流处理链路

整个系统运行在纯内存中，无需外部MQTT Broker，性能优异！
