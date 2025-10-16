'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Bell, LogOut, Search } from 'lucide-react';
import { Button } from '@/components/ui';
import { useUserStore } from '@/stores/userStore';
import { apiClient } from '@/lib/api';
import { clearSession } from '@/utils/auth';

const pageNames: Record<string, string> = {
  '/dashboard': '仪表板',
  '/data-sources': '数据源管理',
  '/target-systems': '目标系统',
  '/routing-rules': '路由规则',
  '/monitoring': '监控中心',
  '/system': '系统管理'
};

export function Header() {
  const pathname = usePathname();
  const pageName = pageNames[pathname] || '主线系统';
  const router = useRouter();
  const user = useUserStore((state) => state.user);
  const setUser = useUserStore((state) => state.setUser);
  const setTokens = useUserStore((state) => state.setTokens);

  const handleLogout = async () => {
    await apiClient.auth.logout();
    clearSession();
    apiClient.setTokens(null, null);
    setTokens({ accessToken: null, refreshToken: null });
    setUser(null);
    router.replace('/login');
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">{pageName}</h2>
          <p className="text-sm text-gray-500 mt-1">
            {new Date().toLocaleDateString('zh-CN', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              weekday: 'long'
            })}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="搜索..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
            />
          </div>

          {/* 通知 */}
          <Button variant="ghost" size="sm" className="relative">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-xs flex items-center justify-center">
              <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
            </span>
          </Button>

          {/* 用户信息 */}
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">
                {user?.fullName || user?.username || '未登录'}
              </p>
              <p className="text-xs text-gray-500 uppercase tracking-wide">
                {user?.role || 'guest'}
              </p>
            </div>
            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold uppercase">
              {(user?.username?.[0] || '?').toUpperCase()}
            </div>
          </div>

          {/* 退出登录 */}
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" />
            退出
          </Button>
        </div>
      </div>
    </header>
  );
}
