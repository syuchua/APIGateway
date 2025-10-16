'use client';

import React, { useEffect } from 'react';
import { Card, Row, Col, Statistic, Badge, Spin, Button, Alert } from 'antd';
import { WifiOutlined, SyncOutlined } from '@ant-design/icons';
import { MetricLineChart } from '@/components/charts';
import { useMonitoringStore } from '@/stores/monitoringStore';

const STATUS_CONFIG: Record<string, { text: string; badge: 'success' | 'warning' | 'error' | 'default'; color: string }> = {
  running: { text: '运行中', badge: 'success', color: 'text-green-600' },
  healthy: { text: '健康', badge: 'success', color: 'text-green-600' },
  warning: { text: '警告', badge: 'warning', color: 'text-yellow-600' },
  critical: { text: '异常', badge: 'error', color: 'text-red-600' },
  stopped: { text: '已停止', badge: 'default', color: 'text-gray-500' },
  unknown: { text: '未知', badge: 'default', color: 'text-gray-500' },
};

const formatNumber = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });

export function RealtimeMonitoringPanel() {
  const realTimeMetrics = useMonitoringStore((state) => state.realTimeMetrics);
  const metricsHistory = useMonitoringStore((state) => state.metricsHistory);
  const fetchMetricsHistory = useMonitoringStore((state) => state.fetchMetricsHistory);
  const loadingMetrics = useMonitoringStore((state) => state.loading.metrics);
  const connectionError = useMonitoringStore((state) => state.connectionError);
  const isConnected = useMonitoringStore((state) => state.isConnected);

  useEffect(() => {
    fetchMetricsHistory('1h');
    const timer = setInterval(() => {
      fetchMetricsHistory('1h').catch(() => {});
    }, 60_000);

    return () => clearInterval(timer);
  }, [fetchMetricsHistory]);

  const handleRefresh = () => {
    fetchMetricsHistory('1h').catch(() => {});
  };

  const metrics = realTimeMetrics ?? {
    gatewayStatus: 'unknown',
    adaptersRunning: 0,
    adaptersTotal: 0,
    forwardersActive: 0,
    messagesPerSecond: 0,
    messagesTotal: 0,
    errorRate: 0,
    cpuUsage: null,
    memoryUsage: null,
  };

  const statusConfig =
    STATUS_CONFIG[metrics.gatewayStatus?.toLowerCase() || 'unknown'] ?? STATUS_CONFIG.unknown;

  const chartData = metricsHistory.map((item) => ({
    timestamp: new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false }),
    value: item.metrics?.received ?? 0,
    success: item.metrics?.success ?? 0,
    failed: item.metrics?.failed ?? 0,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">实时监控</h2>
          <p className="text-sm text-gray-500 mt-1">基于网关事件总线的实时指标与状态</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            status={isConnected ? 'success' : 'error'}
            text={isConnected ? '实时连接' : '连接断开'}
            icon={<WifiOutlined />}
          />
          <Button type="primary" icon={<SyncOutlined />} onClick={handleRefresh} loading={loadingMetrics}>
            刷新
          </Button>
        </div>
      </div>

      {connectionError && (
        <Alert
          type="warning"
          message="实时连接提醒"
          description={connectionError}
          showIcon
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总处理消息"
              value={metrics.messagesTotal}
              valueRender={() => <span className="text-2xl font-semibold text-blue-600">{formatNumber(metrics.messagesTotal)}</span>}
            />
            <div className="mt-2 text-sm text-gray-500">
              当前速率 {formatNumber(metrics.messagesPerSecond)} 条/秒
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="运行中的适配器"
              value={`${metrics.adaptersRunning}/${metrics.adaptersTotal}`}
            />
            <div className="mt-2 text-sm text-gray-500">
              活跃转发器 {metrics.forwardersActive}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="错误率"
              value={metrics.errorRate * 100}
              precision={2}
              suffix="%"
              valueStyle={{ color: metrics.errorRate > 0.05 ? '#cf1322' : '#3f8600' }}
            />
            <div className="mt-2 text-sm text-gray-500">
              最近一分钟统计
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-gray-500 text-sm">网关状态</div>
                <div className={`text-2xl font-semibold ${statusConfig.color}`}>
                  {statusConfig.text}
                </div>
              </div>
              <Badge status={statusConfig.badge} />
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="消息处理趋势（最近一小时）">
        {loadingMetrics ? (
          <div className="flex items-center justify-center h-64">
            <Spin size="large" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-gray-400">
            暂无历史指标数据
          </div>
        ) : (
          <MetricLineChart
            data={chartData}
            dataKey="value"
            stroke="#1890ff"
            unit=" 条/分"
          />
        )}
      </Card>
    </div>
  );
}
