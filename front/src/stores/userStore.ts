import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { User } from '@/types';

interface UserState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setTokens: (tokens: { accessToken?: string | null; refreshToken?: string | null }) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  devtools(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      setUser: (user) => set({ user }),
      setTokens: ({ accessToken, refreshToken }) =>
        set((state) => ({
          accessToken: accessToken ?? state.accessToken,
          refreshToken: refreshToken ?? state.refreshToken,
        })),
      setLoading: (isLoading) => set({ isLoading }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    {
      name: 'user-store',
    }
  )
);
