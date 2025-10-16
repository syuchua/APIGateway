'use client';

import { ReactNode, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useUIStore } from '@/stores/uiStore';
import { useUserStore } from '@/stores/userStore';
import { useWebSocket } from '@/hooks/useWebSocket';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const user = useUserStore((state) => state.user);
  const isLoading = useUserStore((state) => state.isLoading);
  const router = useRouter();

  // 初始化WebSocket连接
  const { error } = useWebSocket({
    autoConnect: true,
    reconnectAttempts: 5,
    reconnectDelay: 3000
  });

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace('/login');
    }
  }, [isLoading, router, user]);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <p className="text-gray-600">正在验证登录状态...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <div className={`transition-all duration-300 ${
        sidebarCollapsed ? 'ml-16' : 'ml-64'
      }`}>
        <Header />

        {/* WebSocket连接状态提示 */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4 mx-6">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-red-700">
                  实时连接异常: {error}
                </p>
              </div>
            </div>
          </div>
        )}

        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
