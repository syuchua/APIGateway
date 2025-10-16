'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUIStore } from '@/stores/uiStore';
import {
  LayoutDashboard,
  Database,
  Target,
  GitBranch,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const navigationItems = [
  {
    name: '仪表板',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: '系统总览和关键指标'
  },
  {
    name: '数据源',
    href: '/data-sources',
    icon: Database,
    description: '管理和配置数据源连接',
    // badge: '3'
  },
  {
    name: '目标系统',
    href: '/target-systems',
    icon: Target,
    description: '配置和管理目标系统'
  },
  {
    name: '路由规则',
    href: '/routing-rules',
    icon: GitBranch,
    description: '数据路由和转换规则'
  },
  {
    name: '监控中心',
    href: '/monitoring',
    icon: Activity,
    description: '实时监控和告警管理'
  },
  {
    name: '系统管理',
    href: '/system',
    icon: Settings,
    description: '系统配置和用户管理'
  }
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <div className={`fixed left-0 top-0 h-full bg-white border-r border-gray-200 transition-all duration-300 z-50 ${
      sidebarCollapsed ? 'w-16' : 'w-64'
    }`}>
      <div className="flex flex-col h-full">
        {/* Logo区域 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          {!sidebarCollapsed && (
            <h1 className="text-xl font-semibold text-gray-900">主线系统</h1>
          )}
          <button
            onClick={toggleSidebar}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            )}
          </button>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-4 space-y-2">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-blue-700' : 'text-gray-500'}`} />

                {!sidebarCollapsed && (
                  <>
                    <span className="font-medium">{item.name}</span>
                    {/* {item.badge && (
                      <span className="ml-auto bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded-full">
                        {item.badge}
                      </span>
                    )} */}
                  </>
                )}

                {sidebarCollapsed && (
                  <div className="absolute left-full ml-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-md opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-50">
                    {item.name}
                    <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1 w-2 h-2 bg-gray-900 rotate-45"></div>
                  </div>
                )}
              </Link>
            );
          })}
        </nav>

        {/* 底部用户信息 */}
        <div className="p-4 border-t border-gray-200">
          {!sidebarCollapsed ? (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-700 text-sm font-medium">管</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">管理员</p>
                <p className="text-xs text-gray-500">admin@system.com</p>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-700 text-sm font-medium">管</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
