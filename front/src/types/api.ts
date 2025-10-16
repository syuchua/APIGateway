export enum ProtocolType {
  UDP = 'UDP',
  HTTP = 'HTTP',
  WEBSOCKET = 'WEBSOCKET',
  MQTT = 'MQTT',
  TCP = 'TCP'
}

// ============ 数据源配置类型 (v2嵌套结构) ============

/** 连接配置 - 基础字段 + 协议特定字段存储在同一个JSONB字段中 */
export interface ConnectionConfig {
  // 基础字段 (所有协议)
  listen_address: string;
  listen_port: number;
  max_connections?: number;
  timeout_seconds?: number;
  buffer_size?: number;

  // HTTP特定字段
  url?: string;
  method?: string;
  headers?: Record<string, string>;

  // UDP特定字段
  forward_mode?: string;
  target_hosts?: string;
  multicast_group?: string;
  multicast_ttl?: number;

  // MQTT特定字段
  topics?: string;
  username?: string;
  password?: string;
  qos?: number;
  broker_host?: string;
  broker_port?: number;

  // WebSocket特定字段
  reconnect_interval?: number;
  max_retries?: number;

  // TCP特定字段
  keep_alive?: boolean;
  host?: string;
  port?: number;

  // 允许其他字段
  [key: string]: unknown;
}

export interface ProfileResponse {
  id: string;
  username: string;
  full_name?: string;
  email?: string;
  role: string;
  permissions: string[];
  avatar?: string;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: ProfileResponse;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

/** 解析配置 */
export interface ParseConfig {
  auto_parse: boolean;
  frame_schema_id?: string | null;
  parse_options?: Record<string, unknown>;
}

// 数据源相关类型
export interface DataSource {
  id: string;
  name: string;
  protocol_type: ProtocolType;
  connection_config: ConnectionConfig;  // v2: 嵌套结构
  parse_config: ParseConfig;            // v2: 嵌套结构
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  status?: 'connected' | 'disconnected' | 'error';
  last_sync?: string;
  data_count?: number;
}

export interface DataSourceStatusPayload {
  id: string;
  name: string;
  protocol_type: string;
  is_active: boolean;
  is_running: boolean;
  stats?: Record<string, unknown> | null;
  total_messages?: number;
  last_message_at?: string | null;
}

export interface CreateDataSourceDto {
  name: string;
  description?: string | null;
  protocol_type: ProtocolType;
  connection_config: ConnectionConfig;
  parse_config?: ParseConfig;
  is_active?: boolean;
}

export interface UpdateDataSourceDto extends Partial<CreateDataSourceDto> {
  // 扩展Partial接口，添加特定属性
  id?: string;
}

// ============ 目标系统配置类型 (v2嵌套结构) ============

/** 端点配置 */
export interface EndpointConfig {
  target_address: string;
  target_port: number;
  endpoint_path?: string;
  use_ssl?: boolean;
}

/** 认证配置 */
export interface AuthConfig {
  auth_type: 'basic' | 'bearer' | 'api_key' | 'custom' | 'none';
  username?: string;
  password?: string;
  token?: string;
  api_key?: string;
  api_key_header?: string;
  custom_headers?: Record<string, string>;
}

/** 转发器配置 */
export interface ForwarderConfig {
  timeout?: number;
  retry_count?: number;
  batch_size?: number;
  compression?: boolean;
  encryption?: ForwarderEncryptionConfig;
}

/** 转发加密配置 */
export interface ForwarderEncryptionConfig {
  enabled: boolean;
  version?: string;
  metadata?: Record<string, unknown>;
}

// 目标系统相关类型
export interface TargetSystem {
  id: string;
  name: string;
  protocol_type: ProtocolType;
  endpoint_config: EndpointConfig;      // v2: 嵌套结构
  auth_config?: AuthConfig;             // v2: 嵌套结构，新增认证配置
  forwarder_config: ForwarderConfig;    // v2: 嵌套结构
  transform_rules?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  status?: 'connected' | 'disconnected' | 'error';
}

export interface CreateTargetSystemDto {
  name: string;
  description?: string | null;
  protocol_type: ProtocolType;
  endpoint_config: EndpointConfig;
  auth_config?: AuthConfig;
  forwarder_config?: ForwarderConfig;
  transform_rules?: Record<string, unknown>;
  is_active?: boolean;
}

export interface UpdateTargetSystemDto extends Partial<CreateTargetSystemDto> {
  // 扩展Partial接口，添加特定属性
  id?: string;
}

// ============ 路由规则相关类型 ============

/** 路由规则简化响应 (用于列表展示) */
export interface RoutingRuleSimple {
  id: string;
  name: string;
  priority: number;
  source_pattern?: string;
  target_system_ids: string[];  // v2: 简化为ID数组
  is_active: boolean;
  is_published: boolean;
  match_count: number;
  last_match_at?: string;
  created_at: string;
  updated_at?: string;
}

/** 路由规则完整响应 */
export interface RoutingRule {
  id: string;
  name: string;
  description?: string;
  priority: number;
  source_config: Record<string, unknown>;
  pipeline: Record<string, unknown>;
  target_systems: Array<{ id: string; [key: string]: unknown }>;
  target_system_ids: string[];
  is_active: boolean;
  is_published: boolean;
  match_count: number;
  last_match_at?: string;
  created_at: string;
  updated_at?: string;
  // 兼容旧版字段
  source_pattern?: string;
  data_type_pattern?: string;
  conditions?: Record<string, unknown>;
}

export interface CreateRoutingRuleDto {
  name: string;
  description?: string;
  priority?: number;
  source_config: Record<string, unknown>;
  pipeline: Record<string, unknown>;
  target_systems: Array<{ id: string; [key: string]: unknown }>;
  is_active?: boolean;
  is_published?: boolean;
  // 兼容旧版
  source_pattern?: string;
  data_type_pattern?: string;
  conditions?: Record<string, unknown>;
}

export interface UpdateRoutingRuleDto extends Partial<CreateRoutingRuleDto> {
  // 扩展Partial接口，添加特定属性
  id?: string;
}

// 监控相关类型
export interface MetricsData {
  timestamp: string;
  metrics: Record<string, number>;
}

export interface LogEntry {
  id: string;
  message_id: string;
  timestamp: string;
  source_protocol: ProtocolType;
  source_id: string;
  target_systems: string[];
  processing_status: string;
  processing_time_ms: number;
  error_message?: string;
  data_size: number;
}

export interface LogFilters {
  start_time?: string;
  end_time?: string;
  source_protocol?: ProtocolType;
  source_id?: string;
  processing_status?: string;
  page?: number;
  limit?: number;
}

export interface SystemHealth {
  timestamp: string;
  overall: 'healthy' | 'warning' | 'critical' | 'stopped' | 'unknown';
  services: Record<string, 'healthy' | 'warning' | 'critical' | 'stopped' | 'unknown'>;
  metrics: {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    connection_count: number;
    message_rate: number;
    error_rate: number;
  };
}

export interface DashboardOverviewTrends {
  connections: number;
  dataTransfer: number;
  successRate: number;
  errors: number;
}

export interface DashboardOverview {
  totalConnections: number;
  dataTransfer: number;
  successRate: number;
  errorCount: number;
  trends: DashboardOverviewTrends;
}

export interface DashboardProtocolStat {
  name: string;
  value: number;
  color: string;
}

export interface DashboardTrafficPoint {
  time: string;
  inbound: number;
  outbound: number;
  total: number;
}

export interface DashboardPerformancePoint {
  hour: string;
  throughput: number;
  latency: number;
  errorRate: number;
}

export interface DashboardAlert {
  id: string;
  level: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: string;
  source: string;
}

export interface DashboardActivity {
  id: string;
  type: 'message' | 'error' | 'create' | 'update' | 'delete' | 'config';
  description: string;
  user: string;
  timestamp: string;
}

export interface DashboardData {
  overview: DashboardOverview;
  protocolStats: DashboardProtocolStat[];
  trafficData: DashboardTrafficPoint[];
  performanceMetrics: DashboardPerformancePoint[];
  systemHealth: SystemHealth;
  alerts: DashboardAlert[];
  recentActivities: DashboardActivity[];
}

export interface EncryptionKey {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  rotated_at?: string | null;
  expires_at?: string | null;
  metadata?: Record<string, string> | null;
}

// 帧格式相关类型
export enum FrameType {
  FIXED = 'FIXED',
  VARIABLE = 'VARIABLE',
  DELIMITED = 'DELIMITED',
}

export enum DataType {
  INT8 = 'INT8',
  UINT8 = 'UINT8',
  INT16 = 'INT16',
  UINT16 = 'UINT16',
  INT32 = 'INT32',
  UINT32 = 'UINT32',
  INT64 = 'INT64',
  UINT64 = 'UINT64',
  FLOAT32 = 'FLOAT32',
  FLOAT64 = 'FLOAT64',
  STRING = 'STRING',
  BYTES = 'BYTES',
  BOOLEAN = 'BOOLEAN',
  TIMESTAMP = 'TIMESTAMP',
}

export enum ByteOrder {
  BIG_ENDIAN = 'BIG_ENDIAN',
  LITTLE_ENDIAN = 'LITTLE_ENDIAN',
}

export enum ChecksumType {
  NONE = 'NONE',
  CRC16 = 'CRC16',
  CRC32 = 'CRC32',
  MD5 = 'MD5',
  SHA256 = 'SHA256',
  SIMPLE_SUM = 'SIMPLE_SUM',
}

export interface FrameFieldConfig {
  name: string;
  data_type: DataType;
  offset: number;
  length: number;
  byte_order: ByteOrder;
  scale?: number;
  offset_value?: number;
  description?: string | null;
}

export interface FrameChecksumConfig {
  type: ChecksumType;
  offset?: number | null;
  length?: number | null;
}

export interface FrameSchema {
  id: string;
  name: string;
  description?: string | null;
  version: string;
  protocol_type: ProtocolType;
  frame_type: FrameType;
  total_length?: number | null;
  fields: FrameFieldConfig[];
  checksum?: FrameChecksumConfig | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateFrameSchemaDto {
  name: string;
  description?: string | null;
  version?: string;
  protocol_type: ProtocolType;
  frame_type: FrameType;
  total_length?: number | null;
  fields: FrameFieldConfig[];
  checksum?: FrameChecksumConfig | null;
  is_published?: boolean;
}

export interface UpdateFrameSchemaDto extends Partial<CreateFrameSchemaDto> {}

// 连接测试相关
export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency?: number;
  timestamp: string;
}

// ============ 统一消息格式 (v2增强字段) ============
export interface UnifiedMessage {
  message_id: string;
  timestamp: string;
  trace_id: string;                     // v2: 新增追踪ID

  source_protocol: ProtocolType;
  source_id: string;
  source_address?: string;              // v2: 新增源地址
  source_port?: number;                 // v2: 新增源端口

  raw_data: string;                     // base64 encoded
  data_size: number;                    // v2: 新增数据大小
  parsed_data?: Record<string, unknown>;
  frame_schema_id?: string;             // v2: 新增帧格式ID

  processing_status: string;
  target_systems: string[];
  routing_rules: string[];              // v2: 改为数组

  error_message?: string;
  error_code?: string;                  // v2: 新增错误代码
  processing_duration_ms?: number;      // v2: 新增处理耗时

  // 兼容旧版字段
  headers?: Record<string, unknown>;
  data_type?: string;
  content_type?: string;
  priority?: number;
}

// ============ API响应格式 (v2统一包装) ============
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  code?: number;
}

export interface PaginatedResponse<T> {
  success: boolean;
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
  message?: string;
  code?: number;
}
