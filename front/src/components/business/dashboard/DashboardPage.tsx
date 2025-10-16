'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  Progress,
  Tag,
  Tooltip as AntdTooltip,
  Skeleton,
  Empty,
  Button,
  Alert
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';

import { TrafficChart, ProtocolPieChart, PerformanceBarChart } from '@/components/charts';
import { apiClient } from '@/lib/api';
import {
  DashboardActivity,
  DashboardAlert,
  DashboardData,
  DashboardOverview,
  SystemHealth
} from '@/types/api';

interface OverviewCardsProps {
  overview?: DashboardOverview;
  loading: boolean;
}

function OverviewCards({ overview, loading }: OverviewCardsProps) {
  const cards = overview
    ? [
        {
          title: '活跃连接',
          value: overview.totalConnections,
          trend: overview.trends.connections,
          suffix: '个',
          icon: <DatabaseOutlined />,
          color: '#1890ff'
        },
        {
          title: '数据传输量 (24h)',
          value: overview.dataTransfer.toFixed(2),
          trend: overview.trends.dataTransfer,
          suffix: ' MB',
          icon: <CloudServerOutlined />,
          color: '#52c41a'
        },
        {
          title: '成功率 (1h)',
          value: overview.successRate.toFixed(2),
          trend: overview.trends.successRate,
          suffix: '%',
          icon: <CheckCircleOutlined />,
          color: '#13c2c2'
        },
        {
          title: '错误消息 (24h)',
          value: overview.errorCount,
          trend: overview.trends.errors,
          suffix: '条',
          icon: <ExclamationCircleOutlined />,
          color: '#f5222d'
        }
      ]
    : [];

  if (loading && !overview) {
    return (
      <Row gutter={[16, 16]}>
        {[1, 2, 3, 4].map((key) => (
          <Col key={key} xs={24} sm={12} lg={6}>
            <Card>
              <Skeleton active paragraph={{ rows: 1 }} />
            </Card>
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {cards.map((card, index) => (
        <Col key={index} xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={card.title}
              value={card.value}
              suffix={card.suffix}
              prefix={card.icon}
              valueStyle={{ color: card.color }}
            />
            <div className="mt-2 flex items-center gap-1">
              {card.trend >= 0 ? (
                <ArrowUpOutlined style={{ color: '#3f8600' }} />
              ) : (
                <ArrowDownOutlined style={{ color: '#cf1322' }} />
              )}
              <span className={`text-sm ${card.trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {Math.abs(card.trend).toFixed(2)}% 较上周期
              </span>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
}

interface TrafficChartCardProps {
  data?: DashboardData['trafficData'];
  loading: boolean;
}

function TrafficChartCard({ data, loading }: TrafficChartCardProps) {
  const trafficData = data ?? [];

  if (loading && !trafficData.length) {
    return <Card title="数据流量趋势 (最近24小时)"><Skeleton active className="h-64" /></Card>;
  }

  if (!trafficData.length) {
    return (
      <Card title="数据流量趋势 (最近24小时)">
        <Empty description="暂无流量数据" />
      </Card>
    );
  }

  const inboundTotal = trafficData.reduce((sum, item) => sum + item.inbound, 0);
  const outboundTotal = trafficData.reduce((sum, item) => sum + item.outbound, 0);
  const peakPoint = trafficData.reduce((prev, curr) =>
    (curr.total ?? curr.inbound + curr.outbound) > (prev.total ?? prev.inbound + prev.outbound)
      ? curr
      : prev
  );
  const averageTotal = (inboundTotal + outboundTotal) / trafficData.length;

  return (
    <Card
      title="数据流量趋势 (最近24小时)"
      extra={
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>入站总量：{inboundTotal.toLocaleString()} 条</span>
          <span>出站总量：{outboundTotal.toLocaleString()} 条</span>
          <span>峰值时段：{peakPoint.time}</span>
        </div>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 text-center">
        <div>
          <div className="text-xs text-gray-500">平均总流量</div>
          <div className="text-lg font-semibold text-gray-900">{averageTotal.toFixed(0)} 条/h</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">峰值流量</div>
          <div className="text-lg font-semibold text-gray-900">
            {(peakPoint.total ?? peakPoint.inbound + peakPoint.outbound).toFixed(0)} 条/h
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500">峰值入站</div>
          <div className="text-lg font-semibold text-blue-600">{peakPoint.inbound.toFixed(0)} 条/h</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">峰值出站</div>
          <div className="text-lg font-semibold text-emerald-600">{peakPoint.outbound.toFixed(0)} 条/h</div>
        </div>
      </div>
      <TrafficChart data={trafficData} showTotal />
    </Card>
  );
}

interface ProtocolDistributionCardProps {
  data?: DashboardData['protocolStats'];
  loading: boolean;
}

function ProtocolDistributionCard({ data, loading }: ProtocolDistributionCardProps) {
  const protocolData = data ?? [];

  if (loading && !protocolData.length) {
    return <Card title="协议分布"><Skeleton active className="h-64" /></Card>;
  }

  if (!protocolData.length) {
    return (
      <Card title="协议分布">
        <Empty description="暂无协议统计" />
      </Card>
    );
  }

  const total = protocolData.reduce((sum, item) => sum + item.value, 0) || 1;
  const sortedProtocols = [...protocolData].sort((a, b) => b.value - a.value);

  return (
    <Card title="协议分布">
      <div className="flex flex-col gap-6">
        <ProtocolPieChart data={protocolData} />
        <div className="space-y-2">
          {sortedProtocols.map((protocol) => {
            const percent = Math.round((protocol.value / total) * 100);
            return (
              <div key={protocol.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: protocol.color }}
                  />
                  <span className="text-sm text-gray-600">{protocol.name}</span>
                </div>
                <div className="flex items-center gap-3 text-sm font-medium text-gray-900">
                  <span>{protocol.value.toLocaleString()} 源</span>
                  <span className="text-xs text-gray-500">{percent}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

interface PerformanceChartCardProps {
  data?: DashboardData['performanceMetrics'];
  loading: boolean;
}

function PerformanceChartCard({ data, loading }: PerformanceChartCardProps) {
  const performanceData = data ?? [];

  if (loading && !performanceData.length) {
    return <Card title="性能指标 (最近12小时)"><Skeleton active className="h-64" /></Card>;
  }

  if (!performanceData.length) {
    return (
      <Card title="性能指标 (最近12小时)">
        <Empty description="暂无性能指标数据" />
      </Card>
    );
  }

  const maxThroughput = Math.max(...performanceData.map((item) => item.throughput));
  const maxThroughputHour = performanceData.find((item) => item.throughput === maxThroughput)?.hour ?? '--';
  const minLatency = Math.min(...performanceData.map((item) => item.latency));
  const avgErrorRate =
    performanceData.reduce((sum, item) => sum + (item.errorRate ?? 0), 0) / performanceData.length;

  return (
    <Card
      title="性能指标 (最近12小时)"
      extra={
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>
            峰值吞吐：{maxThroughput.toFixed(0)} 条
            <Tag color="blue" className="ml-1">
              {maxThroughputHour}
            </Tag>
          </span>
          <span>最低延迟：{minLatency.toFixed(2)} ms</span>
          <span>平均错误率：{avgErrorRate.toFixed(2)}%</span>
        </div>
      }
    >
      <PerformanceBarChart data={performanceData} showErrorRate />
    </Card>
  );
}

type BadgeStatus = 'success' | 'warning' | 'error' | 'default';

interface SystemHealthCardProps {
  systemHealth?: SystemHealth;
  loading: boolean;
}

function SystemHealthCard({ systemHealth, loading }: SystemHealthCardProps) {
  if (loading && !systemHealth) {
    return <Card title="系统健康状态"><Skeleton active className="h-64" /></Card>;
  }

  if (!systemHealth) {
    return (
      <Card title="系统健康状态">
        <Empty description="暂无健康数据" />
      </Card>
    );
  }

  const overallStatus = systemHealth.overall.toLowerCase();
  const statusMap: Record<string, { text: string; badge: BadgeStatus }> = {
    healthy: { text: '正常', badge: 'success' },
    warning: { text: '警告', badge: 'warning' },
    critical: { text: '严重', badge: 'error' },
    stopped: { text: '停止', badge: 'default' },
    unknown: { text: '未知', badge: 'default' },
  };

  const healthItems = [
    { name: 'CPU使用率', value: systemHealth.metrics.cpu_usage, color: systemHealth.metrics.cpu_usage > 80 ? 'red' : systemHealth.metrics.cpu_usage > 60 ? 'orange' : 'blue' },
    { name: '内存使用率', value: systemHealth.metrics.memory_usage, color: systemHealth.metrics.memory_usage > 80 ? 'red' : systemHealth.metrics.memory_usage > 60 ? 'orange' : 'green' },
    { name: '磁盘使用率', value: systemHealth.metrics.disk_usage, color: systemHealth.metrics.disk_usage > 80 ? 'red' : systemHealth.metrics.disk_usage > 60 ? 'orange' : 'yellow' },
  ];

  return (
    <Card title="系统健康状态">
      <div className="flex items-center justify-between mb-4">
        <div>
          <Badge status={statusMap[overallStatus]?.badge ?? 'default'} text={statusMap[overallStatus]?.text ?? '未知'} />
          <div className="text-xs text-gray-500 mt-1">更新时间：{new Date(systemHealth.timestamp).toLocaleString('zh-CN')}</div>
        </div>
      </div>
      <div className="space-y-5">
        {healthItems.map((item, index) => (
          <div key={index}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">{item.name}</span>
              <AntdTooltip title={`当前值：${item.value.toFixed(1)}%`}>
                <Tag
                  color={item.value >= 85 ? 'red' : item.value >= 70 ? 'orange' : item.value >= 40 ? 'blue' : 'green'}
                >
                  {item.value.toFixed(1)}%
                </Tag>
              </AntdTooltip>
            </div>
            <Progress
              percent={item.value}
              strokeColor={item.color}
              showInfo={false}
              status={item.value >= 85 ? 'exception' : item.value >= 70 ? 'active' : 'normal'}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

interface AlertsListProps {
  alerts?: DashboardAlert[];
  loading: boolean;
}

function AlertsList({ alerts, loading }: AlertsListProps) {
  if (loading && !alerts) {
    return <Card title="最新告警"><Skeleton active /></Card>;
  }

  if (!alerts || alerts.length === 0) {
    return (
      <Card title="最新告警">
        <Empty description="暂无告警" />
      </Card>
    );
  }

  const configMap: Record<DashboardAlert['level'], { color: string; bg: string; text: string }> = {
    critical: { color: '#f5222d', bg: 'bg-red-50', text: '严重' },
    warning: { color: '#faad14', bg: 'bg-orange-50', text: '警告' },
    info: { color: '#1890ff', bg: 'bg-blue-50', text: '信息' }
  };

  return (
    <Card title="最新告警">
      <div className="space-y-3">
        {alerts.map((alert) => {
          const config = configMap[alert.level];
          const timestampLabel = alert.timestamp ? new Date(alert.timestamp).toLocaleString('zh-CN') : '未知时间';
          return (
            <div key={alert.id} className={`flex items-center gap-3 p-3 ${config.bg} rounded-lg`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                  <Badge color={config.color} text={config.text} />
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{alert.source}</span>
                  <span>•</span>
                  <span>{timestampLabel}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

interface RecentActivitiesProps {
  activities?: DashboardActivity[];
  loading: boolean;
}

function RecentActivities({ activities, loading }: RecentActivitiesProps) {
  if (loading && !activities) {
    return <Card title="最近活动"><Skeleton active /></Card>;
  }

  if (!activities || activities.length === 0) {
    return (
      <Card title="最近活动">
        <Empty description="暂无活动" />
      </Card>
    );
  }

  const getActivityIcon = (type: DashboardActivity['type']) => {
    switch (type) {
      case 'create':
        return { icon: '➕', className: 'bg-blue-100 text-blue-600' };
      case 'update':
        return { icon: '✏️', className: 'bg-green-100 text-green-600' };
      case 'delete':
        return { icon: '🗑️', className: 'bg-red-100 text-red-600' };
      case 'config':
        return { icon: '⚙️', className: 'bg-purple-100 text-purple-600' };
      case 'error':
        return { icon: '⚠️', className: 'bg-red-100 text-red-600' };
      default:
        return { icon: '📨', className: 'bg-cyan-100 text-cyan-600' };
    }
  };

  return (
    <Card title="最近活动">
      <div className="space-y-3">
        {activities.map((activity) => {
          const iconConfig = getActivityIcon(activity.type);
          const timestampLabel = activity.timestamp ? new Date(activity.timestamp).toLocaleString('zh-CN') : '未知时间';
          return (
            <div key={activity.id} className="flex items-center gap-3">
              <div className={`w-8 h-8 ${iconConfig.className} rounded-full flex items-center justify-center`}>
                <span className="text-sm">{iconConfig.icon}</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{activity.description}</p>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{activity.user}</span>
                  <span>•</span>
                  <span>{timestampLabel}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const {
    data: dashboardData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching
  } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => {
      const response = await apiClient.monitoring.dashboard();
      if (!response.success || !response.data) {
        throw new Error(response.error ?? '仪表板数据加载失败');
      }
      return response.data;
    },
    staleTime: 30_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-800">运行仪表板</h2>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isFetching}>
          刷新
        </Button>
      </div>

      {isError && (
        <Alert
          type="error"
          showIcon
          message="仪表板数据加载失败"
          description={error instanceof Error ? error.message : '请稍后重试'}
        />
      )}

      <OverviewCards overview={dashboardData?.overview} loading={isLoading} />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <TrafficChartCard data={dashboardData?.trafficData} loading={isLoading} />
        </Col>
        <Col xs={24} lg={8}>
          <ProtocolDistributionCard data={dashboardData?.protocolStats} loading={isLoading} />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <PerformanceChartCard data={dashboardData?.performanceMetrics} loading={isLoading} />
        </Col>
        <Col xs={24} lg={8}>
          <SystemHealthCard systemHealth={dashboardData?.systemHealth} loading={isLoading} />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <AlertsList alerts={dashboardData?.alerts} loading={isLoading} />
        </Col>
        <Col xs={24} lg={12}>
          <RecentActivities activities={dashboardData?.recentActivities} loading={isLoading} />
        </Col>
      </Row>
    </div>
  );
}
