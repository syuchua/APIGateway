'use client';

import React from 'react';
import { Card, Col, Row, Statistic, Tag, Tooltip, Progress, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  DatabaseOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  AlertOutlined
} from '@ant-design/icons';

interface SystemOverviewCardProps {
  overview?: {
    uptime: string;
    version: string;
    hostname: string;
    platform: string;
    pythonVersion: string;
    processId: number;
  };
  metrics?: {
    cpu: number;
    memory: number;
    disk: number;
    network: number;
  };
  services?: Array<{ name: string; status: 'healthy' | 'warning' | 'critical' | 'unknown'; detail?: string }>;
  loading?: boolean;
}

interface SystemTask {
  name: string;
  schedule: string;
  lastRun?: string;
  nextRun?: string;
  status: 'idle' | 'running' | 'failed';
  remarks?: string;
}

const statusTagColor: Record<SystemTask['status'], string> = {
  idle: 'blue',
  running: 'green',
  failed: 'red',
};

const defaultServices = [
  { name: '数据库', status: 'unknown' as const, detail: '等待探测' },
  { name: 'Redis 缓存', status: 'unknown' as const, detail: '等待探测' },
  { name: '消息队列', status: 'unknown' as const, detail: '未检测' },
  { name: '定时任务', status: 'unknown' as const, detail: '未检测' },
];

const defaultTasks: SystemTask[] = [
  {
    name: '系统备份',
    schedule: '每天 02:00',
    lastRun: '2024-01-01 02:00',
    nextRun: '2024-01-02 02:00',
    status: 'idle',
  },
  {
    name: '日志压缩',
    schedule: '每 6 小时',
    lastRun: '2024-01-01 12:00',
    nextRun: '2024-01-01 18:00',
    status: 'running',
    remarks: '进行中，约 30 秒完成',
  },
];

const taskColumns: ColumnsType<SystemTask> = [
  {
    title: '任务名称',
    dataIndex: 'name',
    key: 'name',
    width: '20%',
    render: (value) => <span className="font-medium text-gray-800">{value}</span>,
  },
  {
    title: '计划',
    dataIndex: 'schedule',
    key: 'schedule',
    width: '18%',
  },
  {
    title: '上次执行',
    dataIndex: 'lastRun',
    key: 'lastRun',
    width: '18%',
    render: (value?: string) => value ?? '--',
  },
  {
    title: '下次执行',
    dataIndex: 'nextRun',
    key: 'nextRun',
    width: '18%',
    render: (value?: string) => value ?? '--',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: '10%',
    render: (value: SystemTask['status']) => <Tag color={statusTagColor[value]}>{value.toUpperCase()}</Tag>,
  },
  {
    title: '备注',
    dataIndex: 'remarks',
    key: 'remarks',
    render: (value?: string) => value ?? '--',
  }
];

export function SystemOverview({ overview, metrics, services = defaultServices, loading }: SystemOverviewCardProps) {
  return (
    <div className="space-y-6">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card loading={loading} title="系统概览">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic title="系统版本" value={overview?.version ?? '未知'} prefix={<CloudServerOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="运行时长" value={overview?.uptime ?? '--'} prefix={<ThunderboltOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="主机名" value={overview?.hostname ?? '--'} prefix={<DatabaseOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="Python" value={overview?.pythonVersion ?? '--'} prefix={<SafetyCertificateOutlined />} />
              </Col>
            </Row>
            <div className="mt-4 text-xs text-gray-500">
              进程 ID：{overview?.processId ?? '--'} / 平台：{overview?.platform ?? '--'}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card loading={loading} title="资源占用">
            <Row gutter={[16, 16]}>
              {[
                { label: 'CPU 使用率', value: metrics?.cpu ?? 0, color: '#1890ff' },
                { label: '内存使用率', value: metrics?.memory ?? 0, color: '#52c41a' },
                { label: '磁盘使用率', value: metrics?.disk ?? 0, color: '#faad14' },
                { label: '网络繁忙度', value: metrics?.network ?? 0, color: '#722ed1' },
              ].map((item) => (
                <Col span={12} key={item.label}>
                  <Tooltip title={`${item.value.toFixed(1)}%`}>
                    <div className="text-xs text-gray-500 mb-2">{item.label}</div>
                    <Progress percent={Math.round(item.value)} strokeColor={item.color} />
                  </Tooltip>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card loading={loading} title="服务组件状态">
            <div className="space-y-3">
              {services.map((service) => {
                const status = service.status.toLowerCase();
                let tagColor: string = 'default';
                let tagText = '未知';
                if (status === 'healthy') {
                  tagColor = 'success';
                  tagText = '正常';
                } else if (status === 'warning') {
                  tagColor = 'warning';
                  tagText = '警告';
                } else if (status === 'critical') {
                  tagColor = 'error';
                  tagText = '严重';
                }
                return (
                  <div key={service.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertOutlined className="text-gray-400" />
                      <span className="text-sm text-gray-700">{service.name}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      {service.detail && <span>{service.detail}</span>}
                      <Tag color={tagColor}>{tagText}</Tag>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="系统任务" loading={loading}>
            <Table<SystemTask>
              columns={taskColumns}
              dataSource={defaultTasks}
              size="small"
              pagination={false}
              rowKey="name"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
