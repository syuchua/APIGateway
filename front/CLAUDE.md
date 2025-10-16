# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Next.js 15 + React 19 的数据路由管理系统脚手架，使用现代化的技术栈构建。项目采用 App Router 架构，集成了状态管理、数据获取和UI组件系统。

## 核心技术栈

- **框架**: Next.js 15 + React 19 + TypeScript
- **构建工具**: Turbopack (开发) + Webpack (生产)
- **样式**: Tailwind CSS v4 + CSS Modules
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **表单处理**: React Hook Form
- **UI组件**: 自定义组件 + Headless UI
- **图标**: Heroicons + Lucide React
- **图表**: ECharts + Recharts
- **实时通信**: Socket.IO Client

## 项目架构

### 路由结构
项目使用 App Router，主要路由结构：
- `/` - 首页
- `/(dashboard)` - 仪表板布局组
  - `/dashboard` - 主仪表板
  - `/data-sources` - 数据源管理
  - `/target-systems` - 目标系统管理
  - `/routing-rules` - 路由规则配置
  - `/monitoring` - 监控面板
  - `/system` - 系统设置

### 目录结构
- `src/app/` - App Router 页面和布局
- `src/components/` - 可复用组件
  - `ui/` - 基础UI组件（Button, Input, Card等）
  - `layout/` - 布局组件（Sidebar, Header等）
  - `common/` - 通用业务组件
- `src/stores/` - Zustand状态管理
- `src/hooks/` - 自定义React hooks
- `src/lib/` - 第三方库配置和API封装
- `src/utils/` - 工具函数
- `src/types/` - TypeScript类型定义
- `src/styles/` - 样式文件

### 状态管理
使用 Zustand 进行状态管理，主要store包括：
- `userStore.ts` - 用户状态
- `uiStore.ts` - UI状态（侧边栏、主题等）
- `dataSourceStore.ts` - 数据源管理状态
- `monitoringStore.ts` - 监控数据状态

## 常用开发命令

### 启动和构建
```bash
npm run dev          # 启动开发服务器（使用Turbopack）
npm run build        # 构建生产版本（使用Turbopack）
npm start           # 启动生产服务器
```

### 代码质量
```bash
npm run lint        # 运行ESLint检查
npm run lint:fix    # 自动修复ESLint问题
npm run format      # 使用Prettier格式化代码
npm run type-check  # 运行TypeScript类型检查
```

## 开发规范

### 组件开发
- 组件文件使用PascalCase命名（如 `Button.tsx`）
- 组件导出使用命名导出，在 `index.ts` 中统一导出
- 每个组件包含Props接口定义
- 使用 `@/` 路径别名引用src目录

### 状态管理
- 使用Zustand创建类型安全的store
- 开发环境启用devtools中间件
- 保持store职责单一，避免过大的状态对象

### 样式规范
- 优先使用Tailwind CSS类
- 使用 `clsx` 进行条件类名合并
- 复杂样式使用CSS Modules
- 组件样式保持响应式设计

### API集成
- 使用TanStack Query处理数据获取
- API配置在 `src/lib/api/` 目录
- 错误处理统一在查询层处理
- 缓存策略：5分钟staleTime，10分钟gcTime

## 特殊功能

### WebSocket集成
项目集成了Socket.IO客户端，用于实时数据通信：
- WebSocket hooks位于 `src/hooks/useWebSocket.ts`
- 连接管理和消息处理已封装
- 支持自动重连和连接状态管理

### 数据可视化
集成了多个图表库：
- ECharts: 复杂的数据可视化
- Recharts: React组件式图表
- 图表组件统一封装在components中

## 项目配置

### TypeScript配置
- 启用严格模式
- 路径别名 `@/*` 指向 `src/*`
- 增量编译开启

### ESLint配置
- 基于Next.js推荐配置
- 支持TypeScript检查
- 忽略构建目录和类型定义文件

### 开发注意事项
- 默认使用Turbopack，如遇问题可添加 `--no-turbopack` 标志
- 开发端口默认3000
- 支持热重载和快速刷新
- 生产构建前必须通过类型检查和代码检查

## 部署说明
- 推荐使用Vercel部署
- 支持静态导出用于其他平台
- 生产环境变量需要 `NEXT_PUBLIC_` 前缀