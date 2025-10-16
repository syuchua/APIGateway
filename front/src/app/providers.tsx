'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { apiClient } from '@/lib/api';
import { useUserStore } from '@/stores/userStore';
import { clearSession, loadSession, mapProfileToUser } from '@/utils/auth';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: 3,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 1,
      },
    },
  }));

  const router = useRouter();
  const setUser = useUserStore((state) => state.setUser);
  const setTokens = useUserStore((state) => state.setTokens);
  const setLoading = useUserStore((state) => state.setLoading);
  const logout = useUserStore((state) => state.logout);

  useEffect(() => {
    apiClient.setUnauthorizedHandler(() => {
      clearSession();
      setTokens({ accessToken: null, refreshToken: null });
      setUser(null);
      router.replace('/login');
    });
  }, [router, setTokens, setUser]);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      setLoading(true);

      const { accessToken, refreshToken, user } = loadSession();
      if (accessToken) {
        apiClient.setTokens(accessToken, refreshToken ?? null);
        setTokens({ accessToken, refreshToken: refreshToken ?? null });
      }

      if (user) {
        setUser(mapProfileToUser(user));
      }

      if (accessToken) {
        const profileResp = await apiClient.auth.profile();
        if (profileResp.success && profileResp.data && !cancelled) {
          setUser(mapProfileToUser(profileResp.data));
        } else if (!profileResp.success && !cancelled) {
          clearSession();
          logout();
        }
      }

      if (!cancelled) {
        setLoading(false);
      }
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [logout, setLoading, setTokens, setUser]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
