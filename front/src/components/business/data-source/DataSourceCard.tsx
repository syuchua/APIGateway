'use client';

import React from 'react';
import { Card, Tag, Button, Tooltip, Dropdown, Typography, message } from 'antd';
import type { MenuProps } from 'antd';
import {
  MoreOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  PoweroffOutlined,
  EditOutlined,
  DeleteOutlined,
  ExperimentOutlined
} from '@ant-design/icons';
import { DataSource, ProtocolType } from '@/types/api';
import { useDataSourceStore } from '@/stores/dataSourceStore';

interface DataSourceCardProps {
  dataSource: DataSource;
  onEdit: (dataSource: DataSource) => void;
  onDelete: (id: string) => Promise<boolean>;
}

const protocolColors = {
  [ProtocolType.HTTP]: 'blue',
  [ProtocolType.UDP]: 'green',
  [ProtocolType.MQTT]: 'orange',
  [ProtocolType.WEBSOCKET]: 'purple',
  [ProtocolType.TCP]: 'red',
};

const statusColors = {
  connected: 'success',
  disconnected: 'default',
  error: 'error',
} as const;

const statusTexts = {
  connected: '已连接',
  disconnected: '未连接',
  error: '连接异常',
};

export function DataSourceCard({ dataSource, onEdit, onDelete }: DataSourceCardProps) {
  const {
    toggleSource,
    testConnection,
    startSource,
    stopSource,
    runtimeStatus
  } = useDataSourceStore();
  const { Text } = Typography;
  const runtime = runtimeStatus[dataSource.id];
  const isRunning = runtime?.is_running ?? false;
  const totalMessages = runtime?.total_messages ?? dataSource.data_count ?? 0;
  const lastMessageAt = runtime?.last_message_at;

  const handleToggle = async () => {
    await toggleSource(dataSource.id, !dataSource.is_active);
  };

  const handleTest = async () => {
    await testConnection(dataSource.id);
  };

  const handleStartStop = async () => {
    if (!dataSource.is_active) {
      return;
    }
    if (isRunning) {
      await stopSource(dataSource.id);
    } else {
      await startSource(dataSource.id);
    }
  };

  const menuItems = [
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑',
    },
    {
      key: 'test',
      icon: <ExperimentOutlined />,
      label: '测试连接',
    },
    {
      key: 'start-stop',
      icon: isRunning ? <PoweroffOutlined /> : <PlayCircleOutlined />,
      label: isRunning ? '停止运行' : '启动运行',
      disabled: !dataSource.is_active,
    },
    {
      key: 'toggle',
      icon: dataSource.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />,
      label: dataSource.is_active ? '禁用' : '启用',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: '删除',
      danger: true,
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = async ({ key }) => {
    switch (key) {
      case 'edit':
        onEdit(dataSource);
        break;
      case 'test':
        await handleTest();
        break;
      case 'start-stop':
        await handleStartStop();
        break;
      case 'toggle':
        await handleToggle();
        break;
      case 'delete':
        try {
          const success = await onDelete(dataSource.id);
          if (success) {
            message.success('数据源删除成功');
          } else {
            message.error('数据源删除失败');
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : '数据源删除失败';
          message.error(msg);
        }
        break;
      default:
        break;
    }
  };

  const getConnectionInfo = () => {
    const config = dataSource.connection_config;

    // 尝试从多个可能的字段名称中获取地址和端口
    const address = config.listen_address || config.host || config.broker_host || 'localhost';
    const port = config.listen_port || config.port || config.broker_port;
    const url = config.url;

    switch (dataSource.protocol_type) {
      case ProtocolType.HTTP:
        // HTTP可能有url或listen_address+listen_port
        if (url) {
          return url;
        }
        if (port) {
          return `${address}:${port}`;
        }
        return '未配置';

      case ProtocolType.UDP:
      case ProtocolType.TCP:
        // UDP/TCP使用listen_address+listen_port
        if (port) {
          return `${address}:${port}`;
        }
        return '未配置';

      case ProtocolType.MQTT:
        // MQTT使用listen_address+listen_port或broker_host+broker_port
        if (port) {
          return `${address}:${port}`;
        }
        return '未配置';

      case ProtocolType.WEBSOCKET:
        // WebSocket可能有url或listen_address+listen_port
        if (url) {
          return url;
        }
        if (port) {
          return `ws://${address}:${port}`;
        }
        return '未配置';

      default:
        return '未知配置';
    }
  };

  return (
    <Card
      size="small"
      className={`hover:shadow-md transition-shadow ${
        !dataSource.is_active ? 'opacity-60' : ''
      }`}
      actions={[
        <Button
          key="toggle"
          type="text"
          size="small"
          icon={dataSource.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          onClick={handleToggle}
        >
          {dataSource.is_active ? '禁用' : '启用'}
        </Button>,
        <Button
          key="start"
          type="text"
          size="small"
          icon={isRunning ? <PoweroffOutlined /> : <PlayCircleOutlined />}
          onClick={handleStartStop}
          disabled={!dataSource.is_active}
        >
          {isRunning ? '停止' : '启动'}
        </Button>,
        <Button
          key="test"
          type="text"
          size="small"
          icon={<ExperimentOutlined />}
          onClick={handleTest}
        >
          测试
        </Button>,
        <Dropdown
          key="more"
          menu={{ items: menuItems, onClick: handleMenuClick }}
          trigger={['click']}
        >
          <Button type="text" size="small" icon={<MoreOutlined />} />
        </Dropdown>,
      ]}
    >
      <div className="space-y-3">
        {/* 头部信息 */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h4 className="text-base font-medium text-gray-900 mb-1">
              {dataSource.name}
            </h4>
            <div className="flex items-center gap-2">
              <Tag color={protocolColors[dataSource.protocol_type]}>
                {dataSource.protocol_type}
              </Tag>
              {dataSource.status && (
                <Tag color={statusColors[dataSource.status]}>
                  {statusTexts[dataSource.status]}
                </Tag>
              )}
              {!dataSource.is_active && (
                <Tag color="default">已禁用</Tag>
              )}
            </div>
          </div>
        </div>

        {/* 连接信息 */}
        <div className="text-sm text-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span>连接地址:</span>
            <Tooltip title={getConnectionInfo() as string}>
              <span className="font-mono text-xs max-w-[200px] truncate">
                {getConnectionInfo() as string}
              </span>
            </Tooltip>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span>运行状态:</span>
            <Tag color={isRunning ? 'success' : 'default'}>
              {isRunning ? '运行中' : '已停止'}
            </Tag>
          </div>

          {dataSource.last_sync && (
            <div className="flex items-center justify-between mb-1">
              <span>最后同步:</span>
              <span className="text-xs">
                {new Date(dataSource.last_sync).toLocaleString()}
              </span>
            </div>
          )}

          {(lastMessageAt || totalMessages !== undefined) && (
            <div className="flex items-center justify-between">
              <span>累计数据:</span>
              <Text className="text-xs font-medium">
                {Number(totalMessages).toLocaleString()} 条
              </Text>
            </div>
          )}
          {lastMessageAt && (
            <div className="flex items-center justify-between">
              <span>最后消息:</span>
              <span className="text-xs">
                {new Date(lastMessageAt).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {/* 状态指示器 */}
        <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
          <div
            className={`w-2 h-2 rounded-full ${
              !dataSource.is_active
                ? 'bg-gray-300'
                : isRunning
                ? 'bg-green-500'
                : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-gray-500">
            {!dataSource.is_active
              ? '已禁用'
              : isRunning
              ? '运行中'
              : '待启动'}
          </span>
        </div>
      </div>
    </Card>
  );
}
