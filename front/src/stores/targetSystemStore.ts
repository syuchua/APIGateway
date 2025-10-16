import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  TargetSystem,
  CreateTargetSystemDto,
  UpdateTargetSystemDto
} from '@/types/api';
import { apiClient } from '@/lib/api/client';

interface TargetSystemState {
  systems: TargetSystem[];
  loading: boolean;
  error: string | null;

  fetchSystems: () => Promise<void>;
  createSystem: (payload: CreateTargetSystemDto) => Promise<boolean>;
  updateSystem: (id: string, payload: UpdateTargetSystemDto) => Promise<boolean>;
  deleteSystem: (id: string) => Promise<boolean>;
  toggleSystem: (id: string, isActive: boolean) => Promise<boolean>;

  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useTargetSystemStore = create<TargetSystemState>()(
  devtools(
    (set, get) => ({
      systems: [],
      loading: false,
      error: null,

      async fetchSystems() {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.targetSystemsV2.list();
          if (response.success && response.data) {
            set({
              systems: response.data.items || [],
              loading: false
            });
          } else {
            set({
              error: response.error || '获取目标系统列表失败',
              loading: false
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false
          });
        }
      },

      async createSystem(payload) {
        set({ error: null });
        try {
          const response = await apiClient.targetSystemsV2.create(payload);
          if (response.success && response.data) {
            await get().fetchSystems();
            return true;
          }
          set({ error: response.error || '创建目标系统失败' });
          return false;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误'
          });
          return false;
        }
      },

      async updateSystem(id, payload) {
        set({ error: null });
        try {
          const response = await apiClient.targetSystemsV2.update(id, payload);
          if (response.success && response.data) {
            await get().fetchSystems();
            return true;
          }
          set({ error: response.error || '更新目标系统失败' });
          return false;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误'
          });
          return false;
        }
      },

      async deleteSystem(id) {
        set({ error: null });
        try {
          const response = await apiClient.targetSystemsV2.delete(id);
          if (response.success) {
            await get().fetchSystems();
            return true;
          }
          set({ error: response.error || '删除目标系统失败' });
          return false;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误'
          });
          return false;
        }
      },

      async toggleSystem(id, isActive) {
        set({ error: null });
        try {
          if (isActive) {
            const updateResp = await apiClient.targetSystemsV2.update(id, { is_active: true });
            if (!updateResp.success) {
              set({ error: updateResp.error || '启用目标系统失败' });
              return false;
            }

            const startResp = await apiClient.targetSystemsV2.start(id);
            if (!startResp.success) {
              // 尝试回滚启用状态
              await apiClient.targetSystemsV2.update(id, { is_active: false });
              set({ error: startResp.error || '启动目标系统失败' });
              await get().fetchSystems();
              return false;
            }
          } else {
            const stopResp = await apiClient.targetSystemsV2.stop(id);
            if (!stopResp.success) {
              set({ error: stopResp.error || '停止目标系统失败' });
              return false;
            }

            const updateResp = await apiClient.targetSystemsV2.update(id, { is_active: false });
            if (!updateResp.success) {
              set({ error: updateResp.error || '更新目标系统状态失败' });
              return false;
            }
          }

          await get().fetchSystems();
          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误'
          });
          return false;
        }
      },

      setError(error) {
        set({ error });
      },

      clearError() {
        set({ error: null });
      }
    }),
    { name: 'target-system-store' }
  )
);

export default useTargetSystemStore;
