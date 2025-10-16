import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  DataSource,
  CreateDataSourceDto,
  UpdateDataSourceDto,
  DataSourceStatusPayload,
} from '@/types/api';

type DataSourceRuntimeStatus = DataSourceStatusPayload;
import { apiClient } from '@/lib/api';

interface DataSourceState {
  // 数据状态
  sources: DataSource[];
  selectedSource: DataSource | null;
  loading: boolean;
  error: string | null;
  runtimeStatus: Record<string, DataSourceRuntimeStatus>;

  // UI状态
  isCreateModalOpen: boolean;
  isEditModalOpen: boolean;

  // 过滤和搜索
  filters: {
    protocol_type?: string;
    status?: string;
    search?: string;
  };

  // Actions
  fetchSources: () => Promise<void>;
  createSource: (source: CreateDataSourceDto) => Promise<boolean>;
  updateSource: (id: string, source: UpdateDataSourceDto) => Promise<boolean>;
  deleteSource: (id: string) => Promise<boolean>;
  testConnection: (id: string) => Promise<boolean>;
  toggleSource: (id: string, is_active: boolean) => Promise<boolean>;
  startSource: (id: string) => Promise<boolean>;
  stopSource: (id: string) => Promise<boolean>;
  refreshStatus: (id: string) => Promise<DataSourceRuntimeStatus | null>;

  // UI Actions
  selectSource: (source: DataSource | null) => void;
  setCreateModalOpen: (open: boolean) => void;
  setEditModalOpen: (open: boolean) => void;
  setFilters: (filters: Partial<DataSourceState['filters']>) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useDataSourceStore = create<DataSourceState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      sources: [],
      selectedSource: null,
      loading: false,
      error: null,
      runtimeStatus: {},
      isCreateModalOpen: false,
      isEditModalOpen: false,
      filters: {},

      // 数据操作
      fetchSources: async () => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.list(get().filters);
          if (response.success && response.data) {
            const items = response.data.items || [];
            set({ sources: items, loading: false, runtimeStatus: {} });

            // 获取运行状态
            await Promise.all(items.map((item) => get().refreshStatus(item.id)));
          } else {
            set({ error: response.error || '获取数据源失败', loading: false });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false
          });
        }
      },

      createSource: async (source: CreateDataSourceDto) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.create(source);
          if (response.success && response.data) {
            // 重新获取列表
            await get().fetchSources();
            set({ isCreateModalOpen: false, loading: false });
            return true;
          } else {
            set({ error: response.error || '创建数据源失败', loading: false });
            return false;
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false
          });
          return false;
        }
      },

      updateSource: async (id: string, source: UpdateDataSourceDto) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.update(id, source);
          if (response.success) {
            await get().fetchSources();
            set({ isEditModalOpen: false, selectedSource: null, loading: false });
            return true;
          } else {
            set({ error: response.error || '更新数据源失败', loading: false });
            return false;
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false
          });
          return false;
        }
      },

      deleteSource: async (id: string) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.delete(id);
          if (response.success) {
            await get().fetchSources();
            set({ loading: false });
            return true;
          } else {
            set({ error: response.error || '删除数据源失败', loading: false });
            return false;
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '网络错误',
            loading: false
          });
          return false;
        }
      },

      testConnection: async (id: string) => {
        set({ loading: true, error: null });
        try {
          const status = await get().refreshStatus(id);
          set({ loading: false });
          return status !== null;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '连接测试失败',
            loading: false
          });
          return false;
        }
      },

      toggleSource: async (id: string, is_active: boolean) => {
        try {
          // 使用v2 API的update端点
          const response = await apiClient.dataSourcesV2.update(id, { is_active });
          if (response.success) {
            await get().fetchSources();
            return true;
          }
          return false;
        } catch (_error) {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const _ = _error;
          return false;
        }
      },

      startSource: async (id: string) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.start(id);
          if (!response.success) {
            set({ error: response.error || '启动数据源失败', loading: false });
            return false;
          }

          await get().refreshStatus(id);
          set({ loading: false });
          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '启动失败',
            loading: false
          });
          return false;
        }
      },

      stopSource: async (id: string) => {
        set({ loading: true, error: null });
        try {
          const response = await apiClient.dataSourcesV2.stop(id);
          if (!response.success) {
            set({ error: response.error || '停止数据源失败', loading: false });
            return false;
          }

          await get().refreshStatus(id);
          set({ loading: false });
          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '停止失败',
            loading: false
          });
          return false;
        }
      },

      refreshStatus: async (id: string) => {
        try {
          const response = await apiClient.dataSourcesV2.status(id);
          if (response.success && response.data) {
            const status: DataSourceRuntimeStatus = {
              ...response.data,
              stats: response.data.stats ?? null,
              last_message_at: response.data.last_message_at ?? null
            };

            set((state) => ({
              runtimeStatus: {
                ...state.runtimeStatus,
                [id]: status
              }
            }));

            return status;
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '获取运行状态失败'
          });
        }
        return null;
      },

      // UI操作
      selectSource: (source) => set({ selectedSource: source }),
      setCreateModalOpen: (open) => set({ isCreateModalOpen: open }),
      setEditModalOpen: (open) => set({ isEditModalOpen: open }),
      setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters }
      })),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),
    }),
    { name: 'data-source-store' }
  )
);
