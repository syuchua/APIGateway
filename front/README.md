# Next.js 15 标准脚手架文档

## 🚀 项目概述

这是一个基于Next.js 15的标准型前端脚手架，集成了2025年最佳实践的技术栈，适合中型项目开发。

### 📋 技术栈

- **框架**: Next.js 15 + React 19
- **开发语言**: TypeScript
- **样式方案**: Tailwind CSS v4
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **表单处理**: React Hook Form
- **UI组件**: Headless UI + 自定义组件
- **图标**: Heroicons + Lucide React
- **构建工具**: Turbopack
- **代码质量**: ESLint + Prettier

## 📁 项目结构

```
my-nextjs-scaffold/
├── public/                 # 静态资源
├── src/
│   ├── app/               # App Router 路由
│   │   ├── globals.css    # 全局样式
│   │   ├── layout.tsx     # 根布局
│   │   ├── page.tsx       # 首页
│   │   └── providers.tsx  # 全局提供者
│   ├── components/        # 组件目录
│   │   ├── ui/           # 基础UI组件
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── index.ts
│   │   ├── common/       # 通用业务组件
│   │   └── forms/        # 表单组件
│   ├── hooks/            # 自定义Hooks
│   ├── lib/              # 库配置
│   ├── stores/           # 状态管理
│   ├── styles/           # 样式文件
│   ├── types/            # TypeScript类型定义
│   └── utils/            # 工具函数
├── .prettierrc           # Prettier配置
├── eslint.config.mjs     # ESLint配置
├── next.config.ts        # Next.js配置
├── package.json          # 项目依赖
├── postcss.config.mjs    # PostCSS配置
├── tailwind.config.ts    # Tailwind配置
└── tsconfig.json         # TypeScript配置
```

## 🛠️ 快速开始

### 1. 环境要求

- Node.js 22+
- npm 10+

### 2. 安装依赖

```bash
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 [http://localhost:3000](http://localhost:3000) 查看应用。

### 4. 构建生产版本

```bash
npm run build
npm start
```

## 📦 核心依赖说明

### 生产依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| next | 15.5.3 | React框架 |
| react | 19.1.0 | UI库 |
| zustand | ^5.0.8 | 状态管理 |
| @tanstack/react-query | ^5.87.4 | 数据获取和缓存 |
| react-hook-form | ^7.62.0 | 表单处理 |
| @headlessui/react | ^2.2.8 | 无样式UI组件 |
| @heroicons/react | ^2.2.0 | 图标库 |
| clsx | ^2.1.1 | 类名合并工具 |

### 开发依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| typescript | ^5 | 类型检查 |
| tailwindcss | ^4 | CSS框架 |
| eslint | ^9 | 代码检查 |
| prettier | ^3.6.2 | 代码格式化 |
| lucide-react | ^0.544.0 | 图标库 |

## 🎯 核心功能

### 1. 状态管理 (Zustand)

```typescript
// src/stores/userStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface UserState {
  user: User | null;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  devtools((set) => ({
    user: null,
    setUser: (user) => set({ user }),
    logout: () => set({ user: null }),
  }))
);
```

### 2. 数据获取 (TanStack Query)

```typescript
// src/lib/react-query.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5分钟
      gcTime: 10 * 60 * 1000,   // 10分钟
      refetchOnWindowFocus: false,
    },
  },
});
```

### 3. 自定义Hooks

```typescript
// src/hooks/index.ts
export function useLocalStorage<T>(key: string, initialValue: T) {
  // 本地存储hook实现
}

export function useDebounce<T>(value: T, delay: number): T {
  // 防抖hook实现
}
```

### 4. UI组件系统

基于Tailwind CSS构建的组件系统：

- **Button**: 支持多种变体和尺寸的按钮组件
- **Input**: 带标签和错误提示的输入组件
- **LoadingSpinner**: 加载动画组件
- **ErrorMessage**: 错误信息组件

### 5. 工具函数

```typescript
// src/utils/index.ts
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function debounce<T extends (...args: any[]) => void>(
  func: T,
  delay: number
) {
  // 防抖函数实现
}
```

## 🚦 可用脚本

- `npm run dev` - 启动开发服务器（使用Turbopack）
- `npm run build` - 构建生产版本
- `npm start` - 启动生产服务器
- `npm run lint` - 运行ESLint检查
- `npm run lint:fix` - 修复ESLint问题
- `npm run format` - 格式化代码
- `npm run type-check` - TypeScript类型检查

## 🎨 样式规范

### Tailwind CSS配置

项目使用Tailwind CSS v4，支持：

- 响应式设计
- 深色模式支持
- 自定义颜色系统
- 组件样式复用

### CSS类名合并

使用`clsx`进行条件类名合并：

```typescript
import { cn } from '@/utils';

<button
  className={cn(
    'base-styles',
    {
      'active-styles': isActive,
      'disabled-styles': isDisabled,
    },
    className
  )}
>
```

## 📁 文件组织规范

### 组件命名

- 组件文件使用PascalCase: `Button.tsx`
- 组件导出使用命名导出: `export { Button }`
- 每个组件文件包含组件和Props类型定义

### 导入别名

配置了路径别名 `@/*` 指向 `src/*`:

```typescript
import { Button } from '@/components/ui';
import { useUserStore } from '@/stores/userStore';
```

### 类型定义

- 全局类型定义在 `src/types/index.ts`
- 组件特定类型与组件放在同一文件
- 使用接口(interface)而非类型别名(type)

## 🔧 配置说明

### Next.js配置

```typescript
// next.config.ts
const nextConfig = {
  // 启用Turbopack作为默认打包工具
  // 其他配置...
};
```

### TypeScript配置

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    },
    "strict": true,
    "skipLibCheck": true
  }
}
```

### ESLint配置

```javascript
// eslint.config.mjs
import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
```

## 🚀 部署建议

### Vercel部署 (推荐)

1. 连接GitHub仓库到Vercel
2. 自动检测Next.js项目
3. 一键部署

### 其他平台

- **Netlify**: 支持静态导出
- **Docker**: 提供Dockerfile配置
- **传统服务器**: 使用`npm run build && npm start`

## 📈 性能优化

### 内置优化

- **Turbopack**: 极速的开发构建
- **React 19**: 最新性能特性
- **代码分割**: 自动路由级别分割
- **图像优化**: Next.js Image组件
- **字体优化**: next/font自动优化

### 最佳实践

1. 使用动态导入分割大组件
2. 合理使用React.memo和useMemo
3. 图片使用next/image组件
4. 状态尽量保持局部化
5. 避免不必要的重新渲染

## 🔍 开发建议

### 代码质量

1. 启用严格的TypeScript检查
2. 使用ESLint和Prettier保持代码风格
3. 组件保持单一职责
4. 使用自定义Hook提取逻辑

### 测试策略

建议添加测试框架：

```bash
npm install -D @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom
```

### 安全考虑

1. 环境变量使用NEXT_PUBLIC_前缀公开
2. API路由进行适当的验证
3. 第三方包定期更新
4. 生产构建前进行安全审计

## 📚 扩展建议

### 常用扩展包

根据项目需要可添加：

```bash
# 日期处理
npm install date-fns

# 表单验证
npm install zod @hookform/resolvers

# 动画效果
npm install framer-motion

# 图表组件
npm install recharts

# 图标库
npm install @tabler/icons-react
```

### 目录扩展

随着项目增长，可添加：

```
src/
├── constants/     # 常量定义
├── contexts/      # React Context
├── middleware/    # 中间件
├── providers/     # 自定义Provider
├── services/      # API服务层
└── validations/   # 验证模式
```

## 🐛 常见问题

### Q: Turbopack构建失败怎么办？

A: 可以暂时关闭Turbopack使用传统webpack:
```bash
npm run dev -- --no-turbopack
```

### Q: TypeScript类型错误？

A: 运行类型检查命令:
```bash
npm run type-check
```

### Q: 样式不生效？

A: 检查Tailwind配置和CSS导入顺序。

## 📄 许可证

MIT License - 可自由使用和修改。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个脚手架。

---

**创建时间**: 2025年9月14日
**版本**: 1.0.0
**维护者**: Claude Code Assistant
