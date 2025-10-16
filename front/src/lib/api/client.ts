import {
  DataSource,
  CreateDataSourceDto,
  UpdateDataSourceDto,
  TargetSystem,
  CreateTargetSystemDto,
  UpdateTargetSystemDto,
  RoutingRule,
  RoutingRuleSimple,
  CreateRoutingRuleDto,
  UpdateRoutingRuleDto,
  MetricsData,
  LogEntry,
  LogFilters,
  SystemHealth,
  ConnectionTestResult,
  ApiResponse,
  PaginatedResponse,
  DataSourceStatusPayload,
  EncryptionKey,
  FrameSchema,
  CreateFrameSchemaDto,
  UpdateFrameSchemaDto,
  LoginResponse,
  RefreshResponse,
  ProfileResponse,
  DashboardData
} from '@/types/api';

class ApiClient {
  private baseURL: string;
  private token: string | null = null;
  private refreshToken: string | null = null;
  private unauthorizedHandler?: () => void;

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  // 设置认证Token
  setToken(token: string | null) {
    this.token = token;
  }

  setRefreshToken(token: string | null) {
    this.refreshToken = token;
  }

  setTokens(accessToken: string | null, refreshToken: string | null) {
    this.token = accessToken;
    this.refreshToken = refreshToken;
  }

  setUnauthorizedHandler(handler: () => void) {
    this.unauthorizedHandler = handler;
  }

  // 通用请求方法
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      let payload: any = {};
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }

      if (!response.ok) {
        if (response.status === 401 && this.unauthorizedHandler) {
          this.unauthorizedHandler();
        }
        return {
          success: false,
          error: payload.message || payload.detail || `HTTP ${response.status}`,
          code: response.status,
        };
      }

      return {
        success: true,
        data: payload.data || payload,
        message: payload.message,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '网络请求失败',
      };
    }
  }

  private async get<T>(endpoint: string, params?: Record<string, unknown> | LogFilters): Promise<ApiResponse<T>> {
    const url = new URL(`${this.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    return this.request<T>(url.pathname + url.search);
  }

  private async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    });
  }

  // 密钥管理
  encryptionKeys = {
    list: () => this.get<EncryptionKey[]>('/api/v1/encryption-keys'),

    create: (payload: { name: string; description?: string; key_material?: string; is_active?: boolean }) =>
      this.post<EncryptionKey>('/api/v1/encryption-keys', payload),

    activate: (id: string) =>
      this.post(`/api/v1/encryption-keys/${id}/activate`),

    deactivate: (id: string) =>
      this.post(`/api/v1/encryption-keys/${id}/deactivate`),

    delete: (id: string) =>
      this.delete(`/api/v1/encryption-keys/${id}`),
  };

  frameSchemasV2 = {
    list: (params?: { page?: number; limit?: number; protocol_type?: string; is_published?: boolean }) =>
      this.get<PaginatedResponse<FrameSchema>>('/api/v2/frame-schemas', params),

    get: (id: string) =>
      this.get<FrameSchema>(`/api/v2/frame-schemas/${id}`),

    create: (data: CreateFrameSchemaDto) =>
      this.post<FrameSchema>('/api/v2/frame-schemas', data),

    update: (id: string, data: UpdateFrameSchemaDto) =>
      this.put<FrameSchema>(`/api/v2/frame-schemas/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v2/frame-schemas/${id}`),

    publish: (id: string) =>
      this.post<FrameSchema>(`/api/v2/frame-schemas/${id}/publish`),
  };

  // 认证相关API
  auth = {
    login: (username: string, password: string) =>
      this.post<LoginResponse>('/api/v1/auth/login', { username, password }),

    logout: () => this.post('/api/v1/auth/logout'),

    refresh: (refreshToken?: string) => {
      const token = refreshToken ?? this.refreshToken;
      if (!token) {
        return Promise.resolve({
          success: false,
          error: '缺少刷新令牌',
        } as ApiResponse<RefreshResponse>);
      }
      return this.post<RefreshResponse>('/api/v1/auth/refresh', { refresh_token: token });
    },

    profile: () => this.get<ProfileResponse>('/api/v1/auth/profile'),
  };

  // 数据源相关API
  dataSources = {
    list: (params?: { page?: number; limit?: number; protocol_type?: string }) =>
      this.get<PaginatedResponse<DataSource>>('/api/v1/data-sources', params),

    get: (id: string) =>
      this.get<DataSource>(`/api/v1/data-sources/${id}`),

    create: (data: CreateDataSourceDto) =>
      this.post<DataSource>('/api/v1/data-sources', data),

    update: (id: string, data: UpdateDataSourceDto) =>
      this.put<DataSource>(`/api/v1/data-sources/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v1/data-sources/${id}`),

    testConnection: (id: string) =>
      this.post<ConnectionTestResult>(`/api/v1/data-sources/${id}/test`),

    toggle: (id: string, is_active: boolean) =>
      this.put<DataSource>(`/api/v1/data-sources/${id}/toggle`, { is_active }),
  };

  // 目标系统相关API
  targetSystems = {
    list: (params?: { page?: number; limit?: number; protocol_type?: string }) =>
      this.get<PaginatedResponse<TargetSystem>>('/api/v1/target-systems', params),

    get: (id: string) =>
      this.get<TargetSystem>(`/api/v1/target-systems/${id}`),

    create: (data: CreateTargetSystemDto) =>
      this.post<TargetSystem>('/api/v1/target-systems', data),

    update: (id: string, data: UpdateTargetSystemDto) =>
      this.put<TargetSystem>(`/api/v1/target-systems/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v1/target-systems/${id}`),

    testConnection: (id: string) =>
      this.post<ConnectionTestResult>(`/api/v1/target-systems/${id}/test`),

    toggle: (id: string, is_active: boolean) =>
      this.put<TargetSystem>(`/api/v1/target-systems/${id}/toggle`, { is_active }),
  };

  // 路由规则相关API
  routingRules = {
    list: (params?: { page?: number; limit?: number; is_active?: boolean }) =>
      this.get<PaginatedResponse<RoutingRule>>('/api/v1/routing-rules', params),

    get: (id: string) =>
      this.get<RoutingRule>(`/api/v1/routing-rules/${id}`),

    create: (data: CreateRoutingRuleDto) =>
      this.post<RoutingRule>('/api/v1/routing-rules', data),

    update: (id: string, data: UpdateRoutingRuleDto) =>
      this.put<RoutingRule>(`/api/v1/routing-rules/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v1/routing-rules/${id}`),

    toggle: (id: string, is_active: boolean) =>
      this.put<RoutingRule>(`/api/v1/routing-rules/${id}/toggle`, { is_active }),

    reorder: (rules: { id: string; priority: number }[]) =>
      this.put('/api/v1/routing-rules/reorder', { rules }),
  };

  // 监控相关API
  monitoring = {
    metrics: (params?: { timeRange?: string; metrics?: string[] }) =>
      this.get<MetricsData[]>('/api/v1/monitor/metrics', params),

    dashboard: () =>
      this.get<DashboardData>('/api/v1/monitor/dashboard'),

    logs: (filters: LogFilters) =>
      this.get<PaginatedResponse<LogEntry>>('/api/v1/monitor/logs', filters),

    systemHealth: () =>
      this.get<SystemHealth>('/api/v1/monitor/health'),

    alerts: (params?: { severity?: string; status?: string }) =>
      this.get<unknown[]>('/api/v1/monitor/alerts', params),

    // 实时指标流
    metricsStream: () =>
      this.get<unknown>('/api/v1/monitor/metrics/stream'),
  };

  // 系统管理相关API
  system = {
    config: () =>
      this.get<unknown>('/api/v1/system/config'),

    updateConfig: (config: unknown) =>
      this.put('/api/v1/system/config', config),

    restart: () =>
      this.post('/api/v1/system/restart'),

    backup: () =>
      this.post('/api/v1/system/backup'),

    users: () =>
      this.get<unknown[]>('/api/v1/system/users'),

    createUser: (user: unknown) =>
      this.post('/api/v1/system/users', user),
  };

  // ============ API v2 (新的嵌套Schema + ApiResponse包装) ============

  // 数据源相关API v2
  dataSourcesV2 = {
    list: (params?: { page?: number; limit?: number; protocol_type?: string }) =>
      this.get<PaginatedResponse<DataSource>>('/api/v2/data-sources', params),

    get: (id: string) =>
      this.get<DataSource>(`/api/v2/data-sources/${id}`),

    create: (data: CreateDataSourceDto) =>
      this.post<DataSource>('/api/v2/data-sources', data),

    update: (id: string, data: UpdateDataSourceDto) =>
      this.put<DataSource>(`/api/v2/data-sources/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v2/data-sources/${id}`),

    start: (id: string) =>
      this.post<{ status: string }>(`/api/v2/data-sources/${id}/start`),

    stop: (id: string) =>
      this.post<{ status: string }>(`/api/v2/data-sources/${id}/stop`),

    status: (id: string) =>
      this.get<DataSourceStatusPayload>(`/api/v2/data-sources/${id}/status`),
  };

  // 目标系统相关API v2
  targetSystemsV2 = {
    list: (params?: { page?: number; limit?: number; protocol_type?: string }) =>
      this.get<PaginatedResponse<TargetSystem>>('/api/v2/target-systems', params),

    get: (id: string) =>
      this.get<TargetSystem>(`/api/v2/target-systems/${id}`),

    create: (data: CreateTargetSystemDto) =>
      this.post<TargetSystem>('/api/v2/target-systems', data),

    update: (id: string, data: UpdateTargetSystemDto) =>
      this.put<TargetSystem>(`/api/v2/target-systems/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v2/target-systems/${id}`),

    start: (id: string) =>
      this.post<{ status: string }>(`/api/v2/target-systems/${id}/start`),

    stop: (id: string) =>
      this.post<{ status: string }>(`/api/v2/target-systems/${id}/stop`),

    status: (id: string) =>
      this.get<{ status: string; message?: string }>(`/api/v2/target-systems/${id}/status`),
  };

  // 路由规则相关API v2
  routingRulesV2 = {
    /** 获取简化列表（用于UI列表展示） */
    listSimple: (params?: { page?: number; limit?: number; is_active?: boolean; is_published?: boolean }) =>
      this.get<PaginatedResponse<RoutingRuleSimple>>('/api/v2/routing-rules/simple', params),

    /** 获取完整列表 */
    list: (params?: { page?: number; limit?: number; is_active?: boolean; is_published?: boolean }) =>
      this.get<PaginatedResponse<RoutingRule>>('/api/v2/routing-rules', params),

    get: (id: string) =>
      this.get<RoutingRule>(`/api/v2/routing-rules/${id}`),

    create: (data: CreateRoutingRuleDto) =>
      this.post<RoutingRule>('/api/v2/routing-rules', data),

    update: (id: string, data: UpdateRoutingRuleDto) =>
      this.put<RoutingRule>(`/api/v2/routing-rules/${id}`, data),

    delete: (id: string) =>
      this.delete(`/api/v2/routing-rules/${id}`),

    publish: (id: string) =>
      this.post<RoutingRule>(`/api/v2/routing-rules/${id}/publish`),

    unpublish: (id: string) =>
      this.post<RoutingRule>(`/api/v2/routing-rules/${id}/unpublish`),

    reload: (id: string) =>
      this.post<{ status: string }>(`/api/v2/routing-rules/${id}/reload`),
  };
}

// 导出全局API客户端实例
export const apiClient = new ApiClient();
export default ApiClient;
