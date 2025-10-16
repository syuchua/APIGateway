import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { SystemHealth, LogEntry, MetricsData, ProtocolType } from '@/types/api';
import { apiClient } from '@/lib/api';

interface MonitoringState {
  // 实时监控数据
  systemHealth: SystemHealth | null;
  recentLogs: LogEntry[];
  realTimeMetrics: {
    gatewayStatus: string;
    adaptersRunning: number;
    adaptersTotal: number;
    forwardersActive: number;
    messagesPerSecond: number;
    messagesTotal: number;
    errorRate: number;
    cpuUsage?: number | null;
    memoryUsage?: number | null;
  } | null;
  metricsHistory: MetricsData[];

  // WebSocket连接状态
  isConnected: boolean;
  connectionError: string | null;

  // 加载状态
  loading: {
    health: boolean;
    logs: boolean;
    metrics: boolean;
  };

  // 错误状态
  errors: {
    health: string | null;
    logs: string | null;
    metrics: string | null;
  };

  // Actions
  fetchSystemHealth: () => Promise<void>;
  fetchRecentLogs: (limit?: number) => Promise<void>;
  fetchMetricsHistory: (timeRange?: string) => Promise<void>;

  updateRealTimeMetrics: (metrics: Record<string, unknown>) => void;
  addLogEntry: (log: LogEntry) => void;
  updateSystemHealth: (health: SystemHealth) => void;

  // Utility Actions
  setConnectionStatus: (connected: boolean, error?: string) => void;
  clearErrors: () => void;
}

export const useMonitoringStore = create<MonitoringState>()(
  devtools(
    (set, _get) => ({
      // 初始状态
      systemHealth: null,
      recentLogs: [],
      realTimeMetrics: null,
      metricsHistory: [],
      isConnected: false,
      connectionError: null,
      loading: {
        health: false,
        logs: false,
        metrics: false,
      },
      errors: {
        health: null,
        logs: null,
        metrics: null,
      },

      // 数据获取
      fetchSystemHealth: async () => {
        set((state) => ({
          loading: { ...state.loading, health: true },
          errors: { ...state.errors, health: null }
        }));

        try {
          const response = await apiClient.monitoring.systemHealth();
          if (response.success && response.data) {
            set((state) => ({
              systemHealth: response.data,
              loading: { ...state.loading, health: false }
            }));
          } else {
            set((state) => ({
              errors: { ...state.errors, health: response.error || '获取系统健康状态失败' },
              loading: { ...state.loading, health: false }
            }));
          }
        } catch (_error) {
          set((state) => ({
            errors: {
              ...state.errors,
              health: _error instanceof Error ? _error.message : '网络错误'
            },
            loading: { ...state.loading, health: false }
          }));
        }
      },

      fetchRecentLogs: async (limit = 50) => {
        set((state) => ({
          loading: { ...state.loading, logs: true },
          errors: { ...state.errors, logs: null }
        }));

        try {
          const response = await apiClient.monitoring.logs({ limit });
          if (response.success && response.data) {
            set((state) => ({
              recentLogs: response.data?.items || [],
              loading: { ...state.loading, logs: false }
            }));
          } else {
            set((state) => ({
              errors: { ...state.errors, logs: response.error || '获取日志失败' },
              loading: { ...state.loading, logs: false }
            }));
          }
        } catch (_error) {
          set((state) => ({
            errors: {
              ...state.errors,
              logs: _error instanceof Error ? _error.message : '网络错误'
            },
            loading: { ...state.loading, logs: false }
          }));
        }
      },

      fetchMetricsHistory: async (timeRange = '1h') => {
        set((state) => ({
          loading: { ...state.loading, metrics: true },
          errors: { ...state.errors, metrics: null }
        }));

        try {
          const response = await apiClient.monitoring.metrics({ timeRange });
          if (response.success && response.data) {
            set((state) => ({
              metricsHistory: response.data || [],
              loading: { ...state.loading, metrics: false }
            }));
          } else {
            set((state) => ({
              errors: { ...state.errors, metrics: response.error || '获取指标历史失败' },
              loading: { ...state.loading, metrics: false }
            }));
          }
        } catch (_error) {
          set((state) => ({
            errors: {
              ...state.errors,
              metrics: _error instanceof Error ? _error.message : '网络错误'
            },
            loading: { ...state.loading, metrics: false }
          }));
        }
      },

      // WebSocket 相关
      updateRealTimeMetrics: (metrics) => {
        set({
          realTimeMetrics: {
            gatewayStatus: (metrics.gateway_status as string) || 'unknown',
            adaptersRunning: Number(metrics.adapters_running ?? metrics.adaptersRunning ?? 0),
            adaptersTotal: Number(metrics.adapters_total ?? metrics.adaptersTotal ?? 0),
            forwardersActive: Number(metrics.forwarders_active ?? metrics.forwardersActive ?? 0),
            messagesPerSecond: Number(metrics.messages_per_second ?? metrics.messageRate ?? 0),
            messagesTotal: Number(metrics.messages_total ?? metrics.messageCount ?? 0),
            errorRate: Number(metrics.error_rate ?? metrics.errorRate ?? 0),
            cpuUsage: metrics.cpu_usage ?? metrics.cpuUsage ?? null,
            memoryUsage: metrics.memory_usage ?? metrics.memoryUsage ?? null,
          }
        });
      },

      addLogEntry: (log) => {
        set((state) => ({
          recentLogs: [log, ...state.recentLogs.slice(0, 49)] // 保持最新50条
        }));
      },

      updateSystemHealth: (health) => {
        set({ systemHealth: health });
      },

      // 工具方法
      setConnectionStatus: (connected, error) => {
        set({
          isConnected: connected,
          connectionError: error || null
        });
      },

      clearErrors: () => {
        set({
          errors: {
            health: null,
            logs: null,
            metrics: null
          },
          connectionError: null
        });
      },
    }),
    { name: 'monitoring-store' }
  )
);
