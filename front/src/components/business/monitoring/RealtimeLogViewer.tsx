'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Switch, Button, Select, Input, Badge, Tag, Empty, Tooltip } from 'antd';
import {
  PauseOutlined,
  PlayCircleOutlined,
  ClearOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { apiClient } from '@/lib/api';
import type { LogEntry as ApiLogEntry } from '@/types/api';

const { Option } = Select;
const { Search } = Input;

interface ViewerLogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'critical';
  service: string;
  message: string;
  protocol?: string;
  details?: Record<string, unknown>;
}

interface LogFilters {
  level: string[];
  service: string[];
  protocol: string[];
  searchText: string;
}

const normalizeProtocol = (value?: string): string | undefined => {
  if (!value) return undefined;
  let text = String(value);
  if (text.startsWith('ProtocolType.')) {
    text = text.split('.', 2)[1];
  }
  return text.toUpperCase();
};

const transformApiLog = (log: ApiLogEntry): ViewerLogEntry => {
  const level = log.processing_status === 'failed' ? 'error' : 'info';
  return {
    id: log.id,
    timestamp: log.timestamp,
    level: level as ViewerLogEntry['level'],
    service: log.processing_status,
    message: log.message_id,
    protocol: normalizeProtocol(log.source_protocol),
    details: {
      target_systems: log.target_systems,
      error: log.error_message,
      data_size: log.data_size,
    },
  };
};

const transformWsLog = (payload: any): ViewerLogEntry => {
  const extra = payload.data?.extra ?? {};
  const level = payload.data?.level ?? (extra.processing_status === 'failed' ? 'error' : 'info');
  const protocol = normalizeProtocol(extra.source_protocol || payload.data?.source_protocol);
  return {
    id: String(extra.id ?? payload.data?.message ?? `log-${Date.now()}`),
    timestamp: payload.timestamp || new Date().toISOString(),
    level: (level as ViewerLogEntry['level']) ?? 'info',
    service: payload.data?.source || 'gateway',
    message: payload.data?.message || extra.message_id || '',
    protocol,
    details: extra,
  };
};

export function RealtimeLogViewer() {
  const [logs, setLogs] = useState<ViewerLogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filters, setFilters] = useState<LogFilters>({
    level: [],
    service: [],
    protocol: [],
    searchText: ''
  });
  const [isConnected, setIsConnected] = useState(false);

  const logContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const maxLogs = 1000;
  const isPausedRef = useRef(false);

  // WebSocket连接日志流
  const connectLogStream = useCallback(() => {
    // 关闭旧连接
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/logs`;
    console.log('Connecting to log WebSocket:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Log WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        // 处理不同类型的消息
        if (message.type === 'log') {
          const logEntry = transformWsLog(message);

          // 检查isPaused状态再决定是否添加日志
          if (!isPausedRef.current) {
            setLogs(prevLogs => {
              const newLogs = [...prevLogs, logEntry];
              // 保持日志数量在限制范围内
              if (newLogs.length > maxLogs) {
                return newLogs.slice(-maxLogs);
              }
              return newLogs;
            });
          }
        } else if (message.type === 'pong') {
          // 心跳响应，忽略
          console.debug('Received pong from log WebSocket');
        }
      } catch (error) {
        console.error('Error parsing log message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('Log WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = (event) => {
      console.log('Log WebSocket closed', event.code, event.reason);
      setIsConnected(false);

      // 只有在非正常关闭且仍然是当前连接时才重连
      if (wsRef.current === ws && event.code !== 1000) {
        console.log('Attempting to reconnect log WebSocket in 5 seconds...');
        setTimeout(() => {
          if (wsRef.current === ws) {
            connectLogStream();
          }
        }, 5000);
      }
    };
  }, []);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    apiClient.monitoring.logs({ limit: 200 }).then((response) => {
      if (response.success && response.data?.items) {
        const mapped = response.data.items.map(transformApiLog);
        setLogs(mapped.reverse());
      }
    }).catch(() => {});
  }, []);

  // 初始化连接
  useEffect(() => {
    connectLogStream();

    return () => {
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null; // 先清空引用，防止重连
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'Component unmounting'); // 正常关闭
        }
      }
    };
  }, [connectLogStream]);

  // 发送心跳
  useEffect(() => {
    if (!isConnected || !wsRef.current) return;

    const heartbeat = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'ping' }));
      }
    }, 30000); // 每30秒发送一次心跳

    return () => clearInterval(heartbeat);
  }, [isConnected]);

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // 过滤日志
  const filteredLogs = logs.filter(log => {
    if (filters.level.length > 0 && !filters.level.includes(log.level)) {
      return false;
    }
    if (filters.service.length > 0 && !filters.service.includes(log.service)) {
      return false;
    }
    if (filters.protocol.length > 0 && log.protocol && !filters.protocol.includes(log.protocol)) {
      return false;
    }
    if (filters.searchText && !log.message.toLowerCase().includes(filters.searchText.toLowerCase())) {
      return false;
    }
    return true;
  });

  // 获取日志级别的样式
  const getLevelStyle = (level: string) => {
    const styles = {
      debug: { color: 'text-gray-500', bg: 'bg-gray-100' },
      info: { color: 'text-blue-600', bg: 'bg-blue-100' },
      warn: { color: 'text-yellow-600', bg: 'bg-yellow-100' },
      error: { color: 'text-red-600', bg: 'bg-red-100' },
      critical: { color: 'text-red-800', bg: 'bg-red-200' }
    };
    return styles[level as keyof typeof styles] || styles.info;
  };

  // 获取可用的服务列表
  const availableServices = Array.from(new Set(logs.map(log => log.service)));
  const availableProtocols = Array.from(
    new Set(
      logs
        .map(log => normalizeProtocol(log.protocol))
        .filter((value): value is string => Boolean(value))
    )
  );

  // 清空日志
  const clearLogs = () => {
    setLogs([]);
  };

  // 导出日志
  const exportLogs = () => {
    const logText = filteredLogs
      .map(log => `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.service}] ${log.message}`)
      .join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gateway_logs_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 切换暂停/恢复
  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  return (
    <div className="space-y-4">
      {/* 控制栏 */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Badge
                status={isConnected ? "success" : "error"}
                text={isConnected ? "实时连接" : "连接断开"}
              />
              <Tooltip title={isPaused ? "恢复日志流" : "暂停日志流"}>
                <Button
                  type={isPaused ? "primary" : "default"}
                  icon={isPaused ? <PlayCircleOutlined /> : <PauseOutlined />}
                  onClick={togglePause}
                >
                  {isPaused ? "恢复" : "暂停"}
                </Button>
              </Tooltip>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">自动滚动:</span>
              <Switch
                checked={autoScroll}
                onChange={setAutoScroll}
                size="small"
              />
            </div>

            <div className="text-sm text-gray-600">
              显示 {filteredLogs.length} / {logs.length} 条日志
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              icon={<ClearOutlined />}
              onClick={clearLogs}
            >
              清空
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={exportLogs}
              disabled={filteredLogs.length === 0}
            >
              导出
            </Button>
          </div>
        </div>

        {/* 过滤器 */}
        <div className="mt-4 p-4 bg-gray-50 rounded">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">日志级别</label>
              <Select
                mode="multiple"
                placeholder="选择日志级别"
                value={filters.level}
                onChange={(value) => setFilters({ ...filters, level: value })}
                className="w-full"
                size="small"
              >
                <Option value="debug">Debug</Option>
                <Option value="info">Info</Option>
                <Option value="warn">Warn</Option>
                <Option value="error">Error</Option>
                <Option value="critical">Critical</Option>
              </Select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">服务</label>
              <Select
                mode="multiple"
                placeholder="选择服务"
                value={filters.service}
                onChange={(value) => setFilters({ ...filters, service: value })}
                className="w-full"
                size="small"
              >
                {availableServices.map(service => (
                  <Option key={service} value={service}>{service}</Option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">协议</label>
              <Select
                mode="multiple"
                placeholder="选择协议"
                value={filters.protocol}
                onChange={(value) => setFilters({ ...filters, protocol: value })}
                className="w-full"
                size="small"
              >
                {availableProtocols.map(protocol => (
                  <Option key={protocol} value={protocol}>{protocol}</Option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">搜索</label>
              <Search
                placeholder="搜索日志内容"
                value={filters.searchText}
                onChange={(e) => setFilters({ ...filters, searchText: e.target.value })}
                size="small"
                allowClear
              />
            </div>
          </div>
        </div>
      </Card>

      {/* 日志列表 */}
      <Card title="实时日志" className="h-96">
        <div
          ref={logContainerRef}
          className="h-80 overflow-y-auto font-mono text-xs bg-black text-green-400 p-4 rounded"
          style={{ scrollBehavior: autoScroll ? 'smooth' : 'auto' }}
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              {logs.length === 0 ? (
                <Empty
                  description="暂无日志数据"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <Empty
                  description="没有符合条件的日志"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => {
                const levelStyle = getLevelStyle(log.level);
                return (
                  <div key={`${log.id}-${index}`} className="flex items-start gap-2 py-1 hover:bg-gray-800 rounded px-2">
                    <span className="text-gray-400 w-20 flex-shrink-0">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <Tag
                      className={`${levelStyle.color} ${levelStyle.bg} text-xs font-mono w-16 text-center`}
                    >
                      {log.level.toUpperCase()}
                    </Tag>
                    <span className="text-blue-400 w-20 flex-shrink-0 truncate">
                      {log.service}
                    </span>
                    {log.protocol && (
                      <span className="text-yellow-400 w-12 flex-shrink-0 text-xs">
                        {log.protocol.toUpperCase()}
                      </span>
                    )}
                    <span className="flex-1 text-green-400 break-all">
                      {log.message}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
