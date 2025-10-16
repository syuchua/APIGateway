# 测试数据创建脚本

这个目录包含用于快速创建测试数据的脚本，方便测试 API 网关的 v2 API。

## 📁 脚本列表

### 1. `create_test_data_sources.py`
创建 **6 个数据源**，覆盖所有支持的协议类型：

| 数据源 | 协议 | 特点 | 端口 |
|--------|------|------|------|
| HTTP API 数据源 | HTTP | POST 方法，JSON 格式 | 8100 |
| UDP 监听数据源 | UDP | 仅监听模式，二进制数据 | 8001 |
| UDP 单播转发数据源 | UDP | 单播转发模式 | 8002 |
| MQTT 消息队列数据源 | MQTT | 订阅多个主题，QoS=1 | 1883 |
| WebSocket 实时数据源 | WebSocket | 实时数据流 | 8003 |
| TCP 长连接数据源 | TCP | 持久连接，Modbus 协议 | 8005 |

### 2. `create_test_target_systems.py`
创建 **9 个目标系统**，覆盖所有协议和认证类型：

| 目标系统 | 协议 | 认证类型 | 用途 |
|----------|------|----------|------|
| HTTP 数据仓库 | HTTP | none | 内网无认证系统 |
| HTTP API 服务 | HTTP | basic | Basic 认证示例 |
| 云平台 API | HTTP | bearer | Bearer Token 认证 |
| 分析服务 | HTTP | api_key | API Key 认证 |
| 企业系统 | HTTP | custom | 自定义请求头认证 |
| MQTT 消息总线 | MQTT | none | 事件分发 |
| UDP SCADA 系统 | UDP | none | 工控监控 |
| TCP 历史数据库 | TCP | basic | 数据存储 |
| WebSocket 实时看板 | WebSocket | bearer | 实时推送 |

### 3. `create_all_test_data.py`
一键创建所有测试数据（数据源 + 目标系统）

## 🚀 使用方法

### 前置条件

1. 确保后端服务正在运行：
```bash
cd backend
uv run uvicorn app.main:app --reload
```

2. 确保数据库已迁移：
```bash
cd backend
uv run alembic upgrade head
```

### 运行脚本

#### 方式 1：创建所有测试数据（推荐）
```bash
cd backend
uv run python scripts/create_all_test_data.py
```

#### 方式 2：分别创建

**只创建数据源：**
```bash
cd backend
uv run python scripts/create_test_data_sources.py
```

**只创建目标系统：**
```bash
cd backend
uv run python scripts/create_test_target_systems.py
```

## 📊 创建的数据统计

运行 `create_all_test_data.py` 后，您将拥有：

- ✅ **6 个数据源** - 覆盖 HTTP, UDP, MQTT, WebSocket, TCP 协议
- ✅ **9 个目标系统** - 覆盖所有协议和 5 种认证类型
- ✅ **完整的测试场景** - 可以创建各种路由规则进行测试

## 🔧 自定义修改

### 修改端口
编辑脚本中的 `connection_config.listen_port` 或 `endpoint_config.target_port`

### 修改认证信息
编辑脚本中的 `auth_config` 部分

### 添加新的数据源/目标系统
参考现有格式，添加新的字典对象并调用对应的创建函数

## 🧹 清理测试数据

如果需要删除所有测试数据，可以使用以下 SQL：

```sql
-- 删除路由规则
DELETE FROM routing_rules;

-- 删除目标系统
DELETE FROM target_systems;

-- 删除数据源
DELETE FROM data_sources;
```

或者通过前端界面逐个删除。

## 📝 注意事项

1. **端口冲突**：确保脚本中指定的端口未被占用
2. **网络连接**：确保能连接到 `http://localhost:8000`
3. **数据库状态**：脚本会直接插入数据，不会检查重复
4. **错误处理**：如果创建失败，脚本会显示错误信息但继续执行

## 🐛 故障排除

### 错误：无法连接到服务器
- 检查后端服务是否运行：`curl http://localhost:8000/docs`
- 检查端口是否正确：默认 8000

### 错误：422 验证错误
- 检查数据结构是否符合 v2 API 规范
- 查看后端日志获取详细错误信息

### 错误：500 内部服务器错误
- 检查数据库连接
- 查看后端日志：`docker logs <container_id>`

## 🎯 下一步

创建测试数据后，您可以：

1. **访问前端界面**：`http://localhost:3000`
2. **查看数据源列表**：验证所有数据源已创建
3. **查看目标系统列表**：验证所有目标系统已创建
4. **创建路由规则**：将数据源连接到目标系统
5. **测试数据流**：发送测试数据验证路由

## 📚 相关文档

- [API v2 文档](../docs/api_v2.md)
- [数据源配置](../docs/data_sources.md)
- [目标系统配置](../docs/target_systems.md)
- [路由规则配置](../docs/routing_rules.md)
