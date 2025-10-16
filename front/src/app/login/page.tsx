'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

import { apiClient } from '@/lib/api';
import { useUserStore } from '@/stores/userStore';
import { mapProfileToUser, persistSession, clearSession } from '@/utils/auth';

export default function LoginPage() {
  const router = useRouter();
  const setUser = useUserStore((state) => state.setUser);
  const setTokens = useUserStore((state) => state.setTokens);
  const setLoading = useUserStore((state) => state.setLoading);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setLoading(true);

    const response = await apiClient.auth.login(username, password);

    if (response.success && response.data) {
      const { access_token, refresh_token, user } = response.data;

      apiClient.setTokens(access_token, refresh_token);
      setTokens({ accessToken: access_token, refreshToken: refresh_token });
      setUser(mapProfileToUser(user));
      persistSession({ accessToken: access_token, refreshToken: refresh_token, user });

      setLoading(false);
      setSubmitting(false);
      router.replace('/dashboard');
      return;
    }

    clearSession();
    setTokens({ accessToken: null, refreshToken: null });
    setUser(null);
    setLoading(false);
    setSubmitting(false);
    setError(response.error ?? '登录失败，请检查用户名或密码');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">API 网关控制台</h1>
          <p className="text-gray-500 mt-2">请登录以管理数据源、路由与监控</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-gray-700">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入用户名"
              autoComplete="username"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">密码</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入密码"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 border border-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}
