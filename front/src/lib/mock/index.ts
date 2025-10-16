import { MockDataSource, MockTargetSystem, MockMetrics, MockRoutingRule } from '@/types/mock';

// 模拟数据源
export const generateMockDataSources = (): MockDataSource[] => [
  {
    id: '1',
    name: '用户数据库',
    type: 'MySQL',
    status: 'connected',
    host: '192.168.1.100:3306',
    lastSync: '2分钟前',
    dataCount: 150000,
    throughput: 12.5
  },
  {
    id: '2',
    name: '订单系统',
    type: 'PostgreSQL',
    status: 'connected',
    host: '192.168.1.101:5432',
    lastSync: '5分钟前',
    dataCount: 89500,
    throughput: 8.3
  },
  {
    id: '3',
    name: '缓存服务',
    type: 'Redis',
    status: 'error',
    host: '192.168.1.102:6379',
    lastSync: '30分钟前',
    dataCount: 0,
    throughput: 0
  }
];

// 模拟目标系统
export const generateMockTargetSystems = (): MockTargetSystem[] => [
  {
    id: '1',
    name: '数据仓库',
    type: 'Database',
    status: 'active',
    endpoint: 'warehouse.company.com',
    successRate: 98.5,
    latency: 45
  },
  {
    id: '2',
    name: '消息队列',
    type: 'MessageQueue',
    status: 'active',
    endpoint: 'kafka.company.com:9092',
    successRate: 99.2,
    latency: 12
  },
  {
    id: '3',
    name: 'API服务',
    type: 'API',
    status: 'inactive',
    endpoint: 'api.partner.com/webhook',
    successRate: 87.3,
    latency: 156
  },
  {
    id: '4',
    name: '文件存储',
    type: 'FileSystem',
    status: 'error',
    endpoint: 'ftp://files.company.com',
    successRate: 45.2,
    latency: 0
  }
];

// 模拟路由规则
export const generateMockRoutingRules = (): MockRoutingRule[] => [
  {
    id: '1',
    name: '用户数据同步规则',
    description: '将用户数据库的用户信息同步到数据仓库，每5分钟执行一次',
    sourceId: '1',
    targetId: '1',
    status: 'enabled',
    lastExecuted: '2分钟前',
    successRate: 99.2
  },
  {
    id: '2',
    name: '订单数据转发规则',
    description: '实时转发订单数据到消息队列，触发下游业务处理',
    sourceId: '2',
    targetId: '2',
    status: 'enabled',
    lastExecuted: '1分钟前',
    successRate: 98.7
  },
  {
    id: '3',
    name: '日志数据备份规则',
    description: '每日备份应用日志到文件存储系统',
    sourceId: '1',
    targetId: '4',
    status: 'error',
    lastExecuted: '失败 (30分钟前)',
    successRate: 45.2
  }
];

// 生成实时指标数据
export const generateRealtimeMetrics = (): MockMetrics => ({
  timestamp: new Date().toISOString(),
  connections: Math.floor(Math.random() * 20) + 50, // 50-70
  throughput: Math.random() * 10 + 20, // 20-30 MB/s
  successRate: Math.random() * 5 + 95, // 95-100%
  errors: Math.floor(Math.random() * 5),
  cpuUsage: Math.random() * 20 + 40, // 40-60%
  memoryUsage: Math.random() * 30 + 50 // 50-80%
});

// 生成历史指标数据
export const generateHistoricalMetrics = (hours: number = 24): MockMetrics[] => {
  const metrics: MockMetrics[] = [];
  const now = Date.now();

  for (let i = hours; i >= 0; i--) {
    const timestamp = new Date(now - i * 60 * 60 * 1000).toISOString();
    metrics.push({
      timestamp,
      connections: Math.floor(Math.random() * 30) + 40,
      throughput: Math.random() * 15 + 15,
      successRate: Math.random() * 8 + 92,
      errors: Math.floor(Math.random() * 10),
      cpuUsage: Math.random() * 40 + 30,
      memoryUsage: Math.random() * 40 + 40
    });
  }

  return metrics;
};