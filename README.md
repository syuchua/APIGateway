# API Gateway Platform

统一 API Gateway 平台，提供多协议接入、统一处理管道、可视化运维与安全治理能力。项目包含 **FastAPI 后端**、**Next.js 前端**、脚本工具以及基础设施配置，支持数据源接入、目标系统管理、路由编排、加解密、实时监控等核心能力。

---

## 目录结构总览

```
.
├── backend/                 # FastAPI 服务
│   ├── app/
│   │   ├── api/             # v1/v2 REST API（数据源、目标系统、监控、密钥等）
│   │   ├── config/          # 全局配置、日志配置
│   │   ├── core/            # 网关核心：管理器、管道、转发、事件总线
│   │   ├── db/              # 数据库会话、Redis 客户端
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── repositories/    # 数据访问封装
│   │   ├── schemas/         # Pydantic Schemas
│   │   └── services/        # 业务服务（监控、密钥、配置等）
│   ├── scripts/             # 调试工具（创建测试数据源/目标系统/路由规则等）
│   ├── tests/               # 后端测试
│   └── pyproject.toml       # Python 包定义与依赖
├── front/                   # Next.js 15 前端
│   ├── src/app/             # App Router 页面（仪表板、系统管理等）
│   ├── src/components/      # 业务组件 & 图表
│   ├── src/stores/          # Zustand 状态管理
│   └── README.md            # 前端脚手架说明
├── docker-compose.yml       # 示例编排（含 Postgres、Redis、Backend、Front）
├── LOG_AUDIT_PLAN.md        # 审计日志方案草案
├── README.md                # 当前文件
└── TODO.md                  # 待办事项与 Roadmap
```

---

## 系统架构概述

### 核心流程
1. **多协议数据源**：Udp/Tcp/Mqtt/WebSocket/Http 监听器接入外部数据 (`backend/app/core/gateway/adapters`)，解析后发布到事件总线。
2. **处理管道**：`data_pipeline.py` 执行帧解析、校验、路由匹配、转换、加解密等步骤。
3. **目标转发**：根据路由结果织入不同 Forwarder（HTTP/MQTT/TCP 等），支持目标系统认证配置。
4. **监控日志**：`monitoring_service.py` 负责消息日志、指标历史、实时速率统计，暴露 `/api/v1/monitor/*` 接口。
5. **管理平面**：前端仪表板 + 系统管理界面，通过 REST API 完成数据源/目标/密钥管理、系统概览与后续审计日志。

### 核心模块
| 模块 | 说明 |
| ---- | ---- |
| `app/main.py` | FastAPI 应用入口，初始化 Redis、网关管理器、事件总线 |
| `core/gateway/manager.py` | 管理协议适配器生命周期，暴露 start/stop/status |
| `core/gateway/pipeline/*` | 统一数据处理管道，负责解析、转换、路由、加解密 |
| `core/gateway/forwarder/*` | 目标系统转发器，实现 HTTP/MQTT/TCP/WebSocket 等协议 |
| `services/monitoring_service.py` | 消息日志、指标采集、系统健康快照 |
| `services/encryption_key_service.py` | 密钥管理与加解密服务 |
| `api/v1|v2/*` | REST 接口层，v2 提供新一代嵌套 Schema 与统一响应格式 |

前端基于 App Router 架构：
* `/dashboard` 仪表板：统计概览、协议分布、流量趋势、性能、警报&操作。
* `/monitoring` 实时监控：系统健康、实时日志、时序指标。
* `/system` 系统管理：系统概览、密钥管理、用户与角色（在建）、审计日志（规划）。
* `/data-sources`、`/target-systems`、`/routing-rules` 等业务配置页面。

---

## 监控与日志

* **消息日志**：`gateway.message_logs`（分区表），记录数据处理状态、目标系统反馈、错误信息。
* **系统指标**：监控服务维护 `messages_per_second`、`error_rate` 以及 CPU/内存/磁盘使用率快照。
* **审计日志**：`LOG_AUDIT_PLAN.md` 提供方案草案（记录用户敏感操作、系统配置变更等），后续按计划落地独立表 & 前端展示。

---

## 开发与运行

### 本地开发
1. 准备依赖：Python 3.12+、Node.js 22+、PostgreSQL、Redis。
2. Backend：  
   ```bash
   cd backend
   uv pip sync  # 或 python -m venv && pip install -e .
   uv run app/main.py  # 启动 FastAPI
   ```
3. Frontend：  
   ```bash
   cd front
   npm install
   npm run dev
   ```
4. 可选：`backend/scripts` 下提供创建测试数据源/目标系统/路由规则的脚本，现已接入认证。

### 测试
```bash
cd backend
UV_CACHE_DIR=../.uv-cache uv run pytest
```

---

## 部署（多阶段 Docker）

见项目根目录 `Dockerfile`，采用多阶段构建：
1. **builder**：基于 `python:3.12-slim`，创建虚拟环境、安装后端依赖，编译所需的 C 扩展。
2. **runtime**：精简镜像，只包含运行时依赖、应用代码及启动命令，默认使用 `uvicorn app.main:app`.

构建 & 运行示例：
```bash
docker build -t api-gateway .
docker run -p 8000:8000 --env-file backend/.env api-gateway
```

如需同时部署前端，建议单独构建 Next.js 镜像或使用 docker-compose.yml。

---

## 未来计划（摘自 TODO）

- 审计日志：落地数据模型、采集策略、前端展示。
- 系统管理界面：补齐用户/角色操作、任务面板、配置编辑。
- 监控告警：Prometheus 指标保障 + 告警触发。
- API 安全：速率限制、黑白名单、Web 防护策略。

---

## 参考文档

- `后端架构设计.md`：网关详细设计（协议适配、管道、事件总线等）。
- `前端架构设计.md`：Next.js 架构说明（需解压或查看原始文档）。
- `LOG_AUDIT_PLAN.md`：审计日志方案草案。
- `TODO.md`：阶段目标与短期计划。

---

如在使用中遇到问题或希望贡献，共享 Issue/PR 欢迎随时提交。Happy hacking! 🚀
