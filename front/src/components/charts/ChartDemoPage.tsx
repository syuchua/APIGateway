'use client';

import React from 'react';
import { Card, Row, Col, Divider } from 'antd';
import { TrafficChart, ProtocolPieChart, PerformanceBarChart, MetricLineChart } from '@/components/charts';

// 模拟数据
const trafficData = [
  { time: '00:00', inbound: 120, outbound: 80 },
  { time: '01:00', inbound: 150, outbound: 100 },
  { time: '02:00', inbound: 180, outbound: 120 },
  { time: '03:00', inbound: 200, outbound: 140 },
  { time: '04:00', inbound: 160, outbound: 110 },
  { time: '05:00', inbound: 190, outbound: 130 },
];

const protocolData = [
  { name: 'HTTP', value: 45, color: '#1890ff' },
  { name: 'MQTT', value: 25, color: '#52c41a' },
  { name: 'WebSocket', value: 15, color: '#faad14' },
  { name: 'UDP', value: 10, color: '#f5222d' },
  { name: 'TCP', value: 5, color: '#722ed1' },
];

const performanceData = [
  { hour: '00:00', throughput: 500, latency: 20 },
  { hour: '01:00', throughput: 600, latency: 25 },
  { hour: '02:00', throughput: 750, latency: 30 },
  { hour: '03:00', throughput: 800, latency: 28 },
  { hour: '04:00', throughput: 650, latency: 22 },
  { hour: '05:00', throughput: 720, latency: 26 },
];

const metricData = [
  { timestamp: '00:00', value: 50, rate: 100 },
  { timestamp: '00:05', value: 65, rate: 120 },
  { timestamp: '00:10', value: 80, rate: 150 },
  { timestamp: '00:15', value: 75, rate: 140 },
  { timestamp: '00:20', value: 90, rate: 160 },
  { timestamp: '00:25', value: 85, rate: 155 },
];

export function ChartDemoPage() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">图表组件演示</h1>
        <p className="text-gray-600">展示所有可复用的图表组件</p>
      </div>

      <Divider />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="流量趋势图">
            <TrafficChart data={trafficData} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="协议分布图">
            <ProtocolPieChart data={protocolData} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="性能指标柱状图">
            <PerformanceBarChart data={performanceData} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="指标折线图">
            <MetricLineChart
              data={metricData}
              dataKey="value"
              stroke="#52c41a"
              unit=" 个"
            />
          </Card>
        </Col>
      </Row>

      <Card title="不同配置的图表示例">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <div className="border rounded p-4">
              <h4 className="text-lg font-medium mb-3">小尺寸饼图</h4>
              <ProtocolPieChart
                data={protocolData}
                height={200}
                innerRadius={40}
                outerRadius={80}
              />
            </div>
          </Col>
          <Col xs={24} md={12}>
            <div className="border rounded p-4">
              <h4 className="text-lg font-medium mb-3">带错误率的性能图</h4>
              <PerformanceBarChart
                data={performanceData.map(item => ({
                  ...item,
                  errorRate: Math.random() * 5
                }))}
                height={200}
                showErrorRate={true}
              />
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
}