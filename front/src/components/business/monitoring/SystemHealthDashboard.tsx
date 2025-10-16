'use client';

import React, { useEffect, useMemo } from 'react';
import { Card, Row, Col, Badge, Button, Skeleton, Statistic, Progress, Empty, Spin } from 'antd';
import { ReloadOutlined, ApiOutlined, DatabaseOutlined, CloudServerOutlined } from '@ant-design/icons';
import { useMonitoringStore } from '@/stores/monitoringStore';
import { HealthTrendChart } from '@/components/charts';

const STATUS_MAP: Record<string, { text: string; badge: 'success' | 'warning' | 'error' | 'default' }> = {
  healthy: { text: '正常', badge: 'success' },
  warning: { text: '警告', badge: 'warning' },
  critical: { text: '严重', badge: 'error' },
  stopped: { text: '停止', badge: 'default' },
  unknown: { text: '未知', badge: 'default' },
};

const SERVICE_ICON: Record<string, React.ReactNode> = {
  gateway: <ApiOutlined />,
  database: <DatabaseOutlined />,
  redis: <DatabaseOutlined />,
  default: <CloudServerOutlined />,
};

export function SystemHealthDashboard() {
  const systemHealth = useMonitoringStore((state) => state.systemHealth);
  const fetchSystemHealth = useMonitoringStore((state) => state.fetchSystemHealth);
  const metricsHistory = useMonitoringStore((state) => state.metricsHistory);
  const fetchMetricsHistory = useMonitoringStore((state) => state.fetchMetricsHistory);
  const loading = useMonitoringStore((state) => state.loading.health);
  const metricsLoading = useMonitoringStore((state) => state.loading.metrics);

  useEffect(() => {
    fetchSystemHealth();
    fetchMetricsHistory('6h').catch(() => {});
    const interval = setInterval(() => {
      fetchSystemHealth().catch(() => {});
      fetchMetricsHistory('6h').catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, [fetchMetricsHistory, fetchSystemHealth]);

  const handleRefresh = () => {
    fetchSystemHealth().catch(() => {});
    fetchMetricsHistory('6h').catch(() => {});
  };

  const overallStatus =
    STATUS_MAP[(systemHealth?.overall ?? 'unknown').toLowerCase()] ?? STATUS_MAP.unknown;

  const trendData = useMemo(() => {
    return metricsHistory
      .map((item) => {
        const date = new Date(item.timestamp);
        return {
          sortKey: date.getTime(),
          timestamp: date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          cpu: Number(item.metrics.cpu_usage ?? item.metrics.cpuUsage ?? 0),
          memory: Number(item.metrics.memory_usage ?? item.metrics.memoryUsage ?? 0),
          messageRate: Number(item.metrics.message_rate ?? item.metrics.messageRate ?? 0),
          errorRate: Number((item.metrics.error_rate ?? item.metrics.errorRate ?? 0) * 100)
        };
      })
      .sort((a, b) => a.sortKey - b.sortKey)
      .map(({ sortKey, ...rest }) => rest);
  }, [metricsHistory]);

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">系统整体状态</h3>
            <div className="flex items-center gap-2 mt-2">
              <Badge status={overallStatus.badge} text={overallStatus.text} />
              {systemHealth?.timestamp && (
                <span className="text-xs text-gray-500">
                  更新时间: {new Date(systemHealth.timestamp).toLocaleString('zh-CN')}
                </span>
              )}
            </div>
          </div>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新
          </Button>
        </div>
      </Card>

      {loading && !systemHealth ? (
        <Row gutter={[16, 16]}>
          {[1, 2, 3].map((key) => (
            <Col xs={24} sm={12} lg={8} key={key}>
              <Card>
                <Skeleton active />
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {Object.entries(systemHealth?.services ?? {}).map(([name, status]) => {
              const config = STATUS_MAP[status.toLowerCase()] ?? STATUS_MAP.unknown;
              const icon = SERVICE_ICON[name.toLowerCase()] ?? SERVICE_ICON.default;
              return (
                <Col xs={24} sm={12} lg={8} key={name}>
                  <Card>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {icon}
                        <span className="font-medium text-gray-800 capitalize">{name}</span>
                      </div>
                      <Badge status={config.badge} text={config.text} />
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>

          <Card title="运行指标">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="连接数"
                  value={systemHealth?.metrics.connection_count ?? 0}
                  valueStyle={{ fontSize: 24 }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="消息速率"
                  value={(systemHealth?.metrics.message_rate ?? 0).toFixed(2)}
                  suffix=" 条/秒"
                  valueStyle={{ fontSize: 24 }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="错误率"
                  value={((systemHealth?.metrics.error_rate ?? 0) * 100).toFixed(2)}
                  suffix="%"
                  valueStyle={{
                    fontSize: 24,
                    color:
                      (systemHealth?.metrics.error_rate ?? 0) >= 0.05
                        ? '#cf1322'
                        : (systemHealth?.metrics.error_rate ?? 0) >= 0.02
                          ? '#faad14'
                          : undefined
                  }}
                />
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="CPU / 内存"
                  value={`${(systemHealth?.metrics.cpu_usage ?? 0).toFixed(0)}% / ${(systemHealth?.metrics.memory_usage ?? 0).toFixed(0)}%`}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
            </Row>

            <Row gutter={[16, 16]} className="mt-6">
              <Col xs={24} sm={12} md={8}>
                <Card size="small" bordered={false}>
                  <Progress
                    type="dashboard"
                    percent={Math.round(systemHealth?.metrics.cpu_usage ?? 0)}
                    strokeColor={{
                      '0%': '#1890ff',
                      '100%': '#096dd9'
                    }}
                  />
                  <div className="text-center text-sm text-gray-500 mt-2">CPU 使用率</div>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" bordered={false}>
                  <Progress
                    type="dashboard"
                    percent={Math.round(systemHealth?.metrics.memory_usage ?? 0)}
                    strokeColor={{
                      '0%': '#13c2c2',
                      '100%': '#08979c'
                    }}
                  />
                  <div className="text-center text-sm text-gray-500 mt-2">内存使用率</div>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Card size="small" bordered={false}>
                  <Progress
                    type="dashboard"
                    percent={Math.round(systemHealth?.metrics.disk_usage ?? 0)}
                    strokeColor={{
                      '0%': '#faad14',
                      '100%': '#d48806'
                    }}
                  />
                  <div className="text-center text-sm text-gray-500 mt-2">磁盘使用率</div>
                </Card>
              </Col>
            </Row>
          </Card>

          <Card title="趋势分析 (最近 6 小时)">
            {metricsLoading && !trendData.length ? (
              <div className="flex items-center justify-center h-64">
                <Spin />
              </div>
            ) : trendData.length > 0 ? (
              <HealthTrendChart data={trendData} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无趋势数据" />
            )}
          </Card>
        </>
      )}
    </div>
  );
}
