import type { ProfileResponse } from '@/types/api';
import type { User } from '@/types';

export const ACCESS_TOKEN_KEY = 'gateway.access_token';
export const REFRESH_TOKEN_KEY = 'gateway.refresh_token';
export const USER_PROFILE_KEY = 'gateway.user_profile';

export const mapProfileToUser = (profile: ProfileResponse): User => ({
  id: profile.id,
  username: profile.username,
  fullName: profile.full_name ?? undefined,
  email: profile.email ?? undefined,
  role: profile.role,
  permissions: profile.permissions,
  avatar: profile.avatar ?? undefined,
  createdAt: profile.created_at,
  updatedAt: profile.updated_at,
});

export const persistSession = (params: {
  accessToken: string;
  refreshToken: string;
  user: ProfileResponse;
}) => {
  if (typeof window === 'undefined') return;

  localStorage.setItem(ACCESS_TOKEN_KEY, params.accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, params.refreshToken);
  localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(params.user));
};

export const clearSession = () => {
  if (typeof window === 'undefined') return;

  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_PROFILE_KEY);
};

export const loadSession = () => {
  if (typeof window === 'undefined') {
    return {
      accessToken: null,
      refreshToken: null,
      user: null,
    } as const;
  }

  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  const rawProfile = localStorage.getItem(USER_PROFILE_KEY);

  let profile: ProfileResponse | null = null;
  if (rawProfile) {
    try {
      profile = JSON.parse(rawProfile) as ProfileResponse;
    } catch {
      profile = null;
    }
  }

  return {
    accessToken,
    refreshToken,
    user: profile,
  } as const;
};
