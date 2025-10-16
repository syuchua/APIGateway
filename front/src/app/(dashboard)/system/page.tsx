'use client';

import React, { useMemo } from 'react';
import { Tabs, Table, Tag, Button, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';

import { EncryptionKeyManager } from '@/components/system/EncryptionKeyManager';
import { SystemOverview } from '@/components/system/SystemOverview';
import { apiClient } from '@/lib/api';
import type { DashboardData, SystemHealth } from '@/types/api';

interface UserRecord {
  key: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'disabled';
  lastLogin: string;
  createdAt: string;
}

const userColumns: ColumnsType<UserRecord> = [
  {
    title: '用户名',
    dataIndex: 'name',
    key: 'name',
    render: (value: string, record) => (
      <div>
        <div className="text-sm font-medium text-gray-900">{value}</div>
        <div className="text-xs text-gray-500">{record.email}</div>
      </div>
    ),
  },
  {
    title: '角色',
    dataIndex: 'role',
    key: 'role',
    width: 120,
    render: (value: string) => <Tag color={value === '管理员' ? 'red' : 'blue'}>{value}</Tag>,
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 100,
    render: (value: UserRecord['status']) => (
      <Tag color={value === 'active' ? 'green' : 'gray'}>{value === 'active' ? '活跃' : '禁用'}</Tag>
    ),
  },
  {
    title: '最后登录',
    dataIndex: 'lastLogin',
    key: 'lastLogin',
    width: 160,
  },
  {
    title: '创建时间',
    dataIndex: 'createdAt',
    key: 'createdAt',
    width: 160,
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: () => (
      <Space size="middle">
        <Button type="link" size="small">
          编辑
        </Button>
        <Button type="link" size="small">
          重置密码
        </Button>
        <Button type="link" size="small" danger>
          禁用
        </Button>
      </Space>
    ),
  },
];

const defaultUsers: UserRecord[] = [
  {
    key: 'admin',
    name: '系统管理员',
    email: 'admin@example.com',
    role: '管理员',
    status: 'active',
    lastLogin: '刚刚',
    createdAt: '2024-01-01',
  },
];

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '--';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (days) parts.push(`${days}天`);
  if (hours) parts.push(`${hours}小时`);
  if (minutes || parts.length === 0) parts.push(`${minutes}分钟`);
  return parts.join(' ');
}

function computeNetworkUsage(data?: DashboardData['trafficData']): number {
  if (!data || data.length === 0) return 0;
  const recent = data.slice(-4);
  const total = recent.reduce((sum, item) => sum + (item.total ?? item.inbound + item.outbound), 0);
  return total / Math.max(recent.length, 1);
}

export default function SystemPage() {
  const {
    data: dashboardData,
    isLoading,
  } = useQuery({
    queryKey: ['dashboard', 'system-page'],
    queryFn: async () => {
      const response = await apiClient.monitoring.dashboard();
      if (!response.success || !response.data) {
        throw new Error(response.error ?? '仪表板数据加载失败');
      }
      return response.data;
    },
    staleTime: 30_000,
  });

  const overviewProps = useMemo(() => {
    if (!dashboardData) {
      return {
        overview: undefined,
        metrics: undefined,
        services: undefined,
      };
    }

    const systemHealth = dashboardData.systemHealth as SystemHealth | undefined;
    const metrics = systemHealth?.metrics;
    const services = systemHealth
      ? Object.entries(systemHealth.services ?? {}).map(([name, status]) => ({
          name,
          status,
          detail:
            status === 'healthy'
              ? '运行正常'
              : status === 'warning'
                ? '需要关注'
                : status === 'critical'
                  ? '出现异常'
                  : '未检测',
        }))
      : undefined;

    const uptimeSeconds = metrics ? metrics.connection_count * 150 : 0;
    const hostname = typeof window !== 'undefined' ? window.location.hostname : '未获取';
    const platform = typeof window !== 'undefined' ? window.navigator.platform : '未知';

    const networkAverage = computeNetworkUsage(dashboardData.trafficData);
    const networkUsage = Math.min(100, Math.round(networkAverage / 10));

    return {
      overview: {
        uptime: formatDuration(uptimeSeconds),
        version: process.env.NEXT_PUBLIC_APP_VERSION ?? '1.0.0',
        hostname,
        platform,
        pythonVersion: '3.12',
        processId: 1,
      },
      metrics: {
        cpu: metrics?.cpu_usage ?? 0,
        memory: metrics?.memory_usage ?? 0,
        disk: metrics?.disk_usage ?? 0,
        network: networkUsage,
      },
      services,
    };
  }, [dashboardData]);

  const tabs = useMemo(
    () => [
      {
        key: 'overview',
        label: '系统概览',
        children: (
          <SystemOverview
            overview={overviewProps.overview}
            metrics={overviewProps.metrics}
            services={overviewProps.services}
            loading={isLoading}
          />
        ),
      },
      {
        key: 'users',
        label: '用户与角色',
        children: (
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-gray-800">用户列表</h3>
              <Button type="primary" disabled>
                + 创建用户
              </Button>
            </div>
            <Table<UserRecord>
              columns={userColumns}
              dataSource={defaultUsers}
              pagination={false}
              rowKey="key"
              size="small"
            />
          </div>
        ),
      },
      {
        key: 'encryption',
        label: '密钥管理',
        children: <EncryptionKeyManager />,
      },
      // {
      //   key: 'logs',
      //   label: '审计日志',
      //   children: <div className="py-8 text-center text-gray-500">审计日志模块建设中…</div>,
      // },
    ],
    [isLoading, overviewProps],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">系统管理</h2>
          <p className="text-sm text-gray-500">集中管理平台状态、用户与系统配置</p>
        </div>
      </div>

      <Tabs defaultActiveKey="overview" items={tabs} className="bg-white rounded-lg p-6" size="large" />
    </div>
  );
}
