export interface MockDataSource {
  id: string;
  name: string;
  type: 'MySQL' | 'PostgreSQL' | 'Redis' | 'MongoDB' | 'API';
  status: 'connected' | 'disconnected' | 'error';
  host: string;
  lastSync: string;
  dataCount: number;
  throughput: number; // MB/s
}

export interface MockTargetSystem {
  id: string;
  name: string;
  type: 'Database' | 'MessageQueue' | 'API' | 'FileSystem';
  status: 'active' | 'inactive' | 'error';
  endpoint: string;
  successRate: number;
  latency: number; // ms
}

export interface MockMetrics {
  timestamp: string;
  connections: number;
  throughput: number; // MB/s
  successRate: number;
  errors: number;
  cpuUsage: number;
  memoryUsage: number;
}

export interface MockRoutingRule {
  id: string;
  name: string;
  description: string;
  sourceId: string;
  targetId: string;
  status: 'enabled' | 'disabled' | 'error';
  lastExecuted: string;
  successRate: number;
}