# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

统一API网关系统，实现多协议数据接入、处理和分发。系统包含前端管理界面(Next.js 15 + React 19)和后端网关服务(FastAPI + Python)，支持UDP、HTTP、WebSocket、MQTT、TCP等多种协议的数据接入和转发。

## 核心架构

### 系统特性
- **多协议接入**: UDP/HTTP/WebSocket/MQTT/TCP协议数据同时接收
- **EventBus消息总线**: 内存高性能消息传递（替代MQTT内部通信，<0.1ms延迟）
- **协议转换适配**: 统一数据格式处理和协议转换
- **帧数据解析**: 灵活配置数据组帧形式和解析规则（固定长度/可变长度，支持CRC校验）
- **动态路由**: 实时配置数据转发策略和目标系统（规则引擎支持复杂条件）
- **高速分发**: 内存组帧和高并发数据分发（批量转发优化）
- **实时监控**: WebSocket实时推送性能指标和系统状态

### 技术栈
- **前端**: Next.js 15 + React 19 + TypeScript + Tailwind CSS v4 + Zustand + TanStack Query
- **后端**: FastAPI + Python 3.11+ + asyncio
- **数据库**: PostgreSQL 15（主存储） + Redis 7（配置缓存）
- **消息传递**: 内置EventBus（内存）+ MQTT协议支持（外部数据接入）
- **实时通信**: WebSocket（FastAPI原生支持）
- **ORM**: SQLAlchemy 2.0（异步模式）+ Alembic（数据库迁移）

## 项目结构

```
APIGateway/
├── front/                    # 前端 Next.js 应用
│   ├── src/app/             # App Router 页面
│   ├── src/components/      # UI组件
│   ├── src/stores/          # Zustand状态管理
│   ├── package.json         # 前端依赖
│   └── CLAUDE.md            # 前端开发指南
├── backend/                 # 后端 FastAPI 应用
│   ├── app/                 # 应用核心代码
│   │   ├── main.py          # FastAPI主入口
│   │   ├── config/          # 配置管理
│   │   ├── api/             # REST API路由
│   │   ├── core/            # 核心业务逻辑
│   │   │   ├── eventbus/    # EventBus消息总线
│   │   │   └── gateway/     # 网关核心
│   │   │       ├── adapters/    # 协议适配器（UDP/HTTP/WS/TCP/MQTT）
│   │   │       ├── forwarder/   # 数据转发器（HTTP/WS/TCP/UDP/MQTT）
│   │   │       ├── pipeline/    # 数据处理管道
│   │   │       ├── routing/     # 路由引擎
│   │   │       ├── frame/       # 帧解析器
│   │   │       └── manager.py   # 网关管理器
│   │   ├── models/          # SQLAlchemy ORM模型
│   │   ├── schemas/         # Pydantic数据模型
│   │   ├── repositories/    # 数据访问层
│   │   ├── services/        # 业务服务层
│   │   └── db/              # 数据库连接和Redis
│   ├── tests/               # 测试代码（235+测试用例）
│   ├── examples/            # 完整演示示例
│   │   ├── complete_demo.py # 端到端数据流演示
│   │   └── udp_sender.py    # UDP测试数据发送器
│   ├── alembic/             # 数据库迁移脚本
│   └── pyproject.toml       # Python项目配置
├── 需求.md                   # 系统需求文档
├── 后端架构设计.md           # 后端架构设计（2200+行）
├── 前端架构设计.md           # 前端架构设计
└── TODO.md                  # 开发进度和待办事项
```

## 常用开发命令

### 前端开发
```bash
cd front
npm run dev          # 启动开发服务器 (端口3001, Turbopack)
npm run build        # 构建生产版本
npm run lint         # ESLint代码检查
npm run type-check   # TypeScript类型检查
```

### 后端开发
```bash
cd backend

# 使用uv管理依赖（推荐）
uv venv                          # 创建虚拟环境
source .venv/bin/activate        # 激活虚拟环境 (Linux/Mac)
# .venv\Scripts\activate         # Windows
uv pip install -e ".[dev]"       # 安装开发依赖

# 启动后端服务
python app/main.py               # 启动FastAPI服务 (端口8000)
uvicorn app.main:app --reload    # 使用uvicorn启动（热重载）

# 运行完整示例
python examples/complete_demo.py # 启动网关完整示例
python examples/udp_sender.py    # 发送UDP测试数据（另一终端）

# 测试
pytest                           # 运行所有测试（235+测试）
pytest tests/test_eventbus.py    # 运行单个测试文件
pytest --cov=app --cov-report=html  # 生成覆盖率报告

# 数据库迁移
alembic revision --autogenerate -m "描述"  # 生成迁移脚本
alembic upgrade head                      # 执行迁移
alembic downgrade -1                      # 回滚一个版本
```

### Docker环境
```bash
cd backend
docker-compose up -d postgres redis  # 启动PostgreSQL和Redis
docker-compose down                  # 停止所有容器
docker-compose logs -f postgres      # 查看PostgreSQL日志
```

## 核心概念

### EventBus消息总线
内存高性能消息传递系统（替代MQTT内部通信）：
- **性能优势**: <0.1ms延迟（MQTT为5-50ms），1M+/s吞吐量
- **线程安全**: RLock保证并发安全
- **主题定义**: `app/core/eventbus/topics.py`（如DATA_RAW, DATA_PARSED, DATA_ROUTED等）
- **发布订阅**: 组件间解耦通信

```python
from app.core.eventbus import get_eventbus, Topics

eventbus = get_eventbus()
eventbus.subscribe(Topics.DATA_RAW, callback_function)
eventbus.publish(Topics.DATA_PARSED, {"message": data})
```

### 统一数据格式 (UnifiedMessage)
所有协议数据转换为统一格式处理：
```python
class UnifiedMessage:
    message_id: str
    timestamp: datetime
    source_protocol: ProtocolType  # UDP/HTTP/WebSocket/MQTT/TCP
    source_id: str
    raw_data: bytes
    parsed_data: Optional[Dict]    # 帧解析后数据
    target_systems: List[str]      # 路由目标系统
    processing_status: ProcessingStatus
```

### 工厂模式架构
协议适配器和转发器使用工厂模式动态创建：
```python
# 适配器工厂
from app.core.gateway.adapters.factory import create_adapter
adapter = await create_adapter("UDP", adapter_id, config)

# 转发器工厂
from app.core.gateway.forwarder.factory import create_forwarder
forwarder = await create_forwarder("HTTP", forwarder_id, config)
```

### 数据处理流程
```
数据接入 → 帧解析 → 路由匹配 → 数据转换 → 批量转发
   ↓         ↓         ↓          ↓          ↓
 Adapter  Parser   Router   Transformer  Forwarder
   ↓         ↓         ↓          ↓          ↓
EventBus: DATA_RAW → DATA_PARSED → DATA_ROUTED → DATA_TRANSFORMED → DATA_OUTPUT
```

## 关键文件说明

### 后端核心文件
- `backend/app/main.py`: FastAPI主入口，注册路由和WebSocket端点
- `backend/app/core/eventbus/eventbus.py`: EventBus核心实现（高性能消息总线）
- `backend/app/core/gateway/manager.py`: 网关管理器（统一管理所有组件）
- `backend/app/core/gateway/pipeline/data_pipeline.py`: 数据处理管道编排
- `backend/app/core/gateway/routing/engine.py`: 路由引擎（规则匹配和条件评估）
- `backend/app/core/gateway/frame/parser.py`: 帧解析器（支持多种数据类型和CRC校验）
- `backend/app/db/database.py`: 数据库连接管理（AsyncEngine + 会话工厂）
- `backend/app/repositories/base.py`: Repository基类（CRUD操作模板）
- `backend/app/services/configuration.py`: 配置管理服务（数据库加载+Redis缓存）

### 设计文档
- `后端架构设计.md`: 完整的后端架构设计（2200+行，包含EventBus设计、数据库schema、API设计）
- `前端架构设计.md`: 前端技术架构和组件设计
- `需求.md`: 系统功能需求和互联互通互操作要求
- `TODO.md`: 开发进度跟踪（实时更新）

### 示例和测试
- `backend/examples/complete_demo.py`: 完整数据流演示（UDP接收→解析→路由→HTTP转发）
- `backend/QUICKSTART.md`: 快速运行指南
- `backend/tests/`: 235+测试用例（79%整体覆盖率）

## API端点

### REST API (http://localhost:8000)
- **数据源管理**: `/api/v1/data-sources/*` (6个端点)
- **目标系统管理**: `/api/v1/target-systems/*` (5个端点)
- **路由规则管理**: `/api/v1/routing-rules/*` (7个端点)
- **帧格式管理**: `/api/v1/frame-schemas/*` (待开发)
- **监控统计**: `/api/v1/stats/*` (5个端点)
- **健康检查**: `/health`, `/status`

### WebSocket实时推送 (ws://localhost:8000)
- `/ws/monitor`: 实时性能指标（每2秒推送）
- `/ws/logs`: 实时日志流
- `/ws/messages`: 实时消息数据流

### API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 数据库设计

### PostgreSQL Schema: `gateway`
- **data_sources**: 数据源配置（协议类型、连接配置、帧格式ID）
- **target_systems**: 目标系统配置（端点配置、认证配置、转发配置）
- **routing_rules**: 路由规则（条件配置、目标系统、优先级）
- **frame_schemas**: 帧格式定义（字段定义、校验规则、版本管理）
- **message_logs**: 消息处理日志（分区表，按时间戳分区）
- **forward_logs**: 转发日志（目标系统、状态、错误信息）
- **routing_rule_logs**: 路由日志（规则执行记录）

### Redis缓存策略
- **配置缓存**: `config:{type}:{id}` (1小时TTL)
- **会话缓存**: `session:{id}` (2小时TTL)
- **实时指标**: `metrics:{service}:{name}` (5分钟TTL)

## 测试策略

### 测试结构
- **单元测试**: `tests/test_*.py` (组件级别测试)
- **集成测试**: `tests/test_*_integration.py` (跨组件测试)
- **API测试**: `tests/quick_*_test.py` (快速API验证)
- **示例测试**: `examples/` (端到端完整流程)

### 运行测试
```bash
# 运行所有测试
pytest

# 运行单个模块测试
pytest tests/test_eventbus.py -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行特定标记的测试
pytest -m "not slow"  # 跳过慢速测试
```

### 当前测试状态
- **总测试数**: 235+
- **通过率**: 100%
- **整体覆盖率**: 79%
- **核心组件覆盖率**: 80-100%

## 开发规范

### Python代码规范
- 使用Black格式化（88字符行宽）
- 使用isort排序导入
- 遵循PEP 8和类型注解
- 异步函数使用`async/await`
- 组件使用依赖注入模式

### 命名约定
- 模块/包: `snake_case`
- 类: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `UPPER_SNAKE_CASE`
- 私有成员: `_leading_underscore`

### 提交规范
- 使用中文描述提交信息
- 格式: `<类型>: <简短描述>`
- 类型: `feat`/`fix`/`refactor`/`test`/`docs`/`chore`

## 性能指标

### EventBus vs MQTT
| 指标 | MQTT | EventBus | 提升 |
|------|------|----------|------|
| 延迟 | 5-50ms | <0.1ms | **500x** |
| 吞吐量 | 10K-100K/s | 1M+/s | **10-100x** |
| CPU占用 | 中等 | 极低 | **10x** |

### 性能目标
- 支持高并发数据接入（万级QPS）
- 毫秒级数据处理延迟（p95 < 10ms）
- 高可用性（99.9%系统可用性）

## 常见问题

### 数据库连接
- PostgreSQL端口: `15432` (Docker映射)
- 数据库名: `gateway`
- Schema: `gateway`
- 默认用户: `postgres/postgres`

### Redis连接
- 端口: `6379`
- 数据库: `0`（默认）

### 测试环境
- 使用pytest-asyncio处理异步测试
- 使用pytest-mock进行模拟
- 测试数据库需要手动创建schema

## 注意事项

1. **协议支持**: 所有主流协议适配器和转发器已实现（UDP/HTTP/WebSocket/TCP/MQTT）
2. **工厂模式**: 新增协议需要继承`BaseAdapter`/`BaseForwarder`并注册到工厂
3. **EventBus**: 内部消息传递使用EventBus（不依赖外部MQTT），外部MQTT仅用于数据接入
4. **数据库迁移**: 修改模型后需要生成Alembic迁移脚本
5. **配置缓存**: 配置更新后需要调用`invalidate_cache()`清除Redis缓存
6. **异步编程**: FastAPI和SQLAlchemy均使用异步模式，注意`await`关键字
7. **Docker环境**: 本地开发推荐使用Docker启动PostgreSQL和Redis

## 开发进度

当前项目状态（参考 TODO.md）：
- ✅ EventBus核心实现（100%测试通过）
- ✅ 5种协议适配器（UDP/HTTP/WebSocket/TCP/MQTT）
- ✅ 5种数据转发器（HTTP/WebSocket/TCP/UDP/MQTT）
- ✅ 数据处理管道（解析/路由/转换）
- ✅ 数据库集成（PostgreSQL + Redis）
- ✅ REST API（数据源/目标系统/路由规则管理）
- ✅ WebSocket实时推送
- ⏳ 帧格式管理API（待开发）
- ⏳ JWT认证授权（待开发）

详细开发进度和待办事项请参考 `TODO.md`。
