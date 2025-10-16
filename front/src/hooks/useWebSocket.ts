'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useMonitoringStore } from '@/stores/monitoringStore';
import { LogEntry, ProtocolType, SystemHealth } from '@/types/api';

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

interface WebSocketState {
  socket: WebSocket | null;
  isConnected: boolean;
  error: string | null;
  reconnectCount: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/monitor',
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectDelay = 3000
  } = options;

  const [state, setState] = useState<WebSocketState>({
    socket: null,
    isConnected: false,
    error: null,
    reconnectCount: 0
  });

  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const shouldReconnect = useRef(true);

  // 从 store 获取方法
  const setConnectionStatus = useMonitoringStore((state) => state.setConnectionStatus);
  const updateRealTimeMetrics = useMonitoringStore((state) => state.updateRealTimeMetrics);
  const addLogEntry = useMonitoringStore((state) => state.addLogEntry);
  const updateSystemHealth = useMonitoringStore((state) => state.updateSystemHealth);

  const mapLogMessage = useCallback((payload: any): LogEntry | null => {
    if (!payload?.data) {
      return null;
    }

    const extras = payload.data.extra ?? {};
    const protocolKey = String(extras.source_protocol ?? 'UDP').toUpperCase();
    const protocolMap = ProtocolType as unknown as Record<string, ProtocolType>;
    const sourceProtocol = protocolMap[protocolKey] ?? ProtocolType.UDP;

    return {
      id: String(extras.id ?? payload.data.message ?? `log-${Date.now()}`),
      message_id: String(extras.message_id ?? payload.data.message ?? ''),
      timestamp: payload.timestamp || new Date().toISOString(),
      source_protocol: sourceProtocol,
      source_id: String(extras.source_id ?? ''),
      target_systems: Array.isArray(extras.target_systems)
        ? extras.target_systems.map((id: unknown) => String(id))
        : [],
      processing_status: String(extras.processing_status ?? payload.data.level ?? 'info'),
      processing_time_ms: Number(extras.processing_time_ms ?? 0),
      error_message: extras.error ?? payload.data.extra?.error ?? null,
      data_size: Number(extras.raw_data_size ?? 0)
    };
  }, []);

  const connect = useCallback(() => {
    if (state.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    console.log('Connecting to WebSocket...', url);

    try {
      const newSocket = new WebSocket(url);

      // 连接打开
      newSocket.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({
          ...prev,
          socket: newSocket,
          isConnected: true,
          error: null,
          reconnectCount: 0
        }));
        setConnectionStatus(true);
      };

      // 接收消息
      newSocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          switch (payload.type) {
            case 'monitor':
              if (payload.data) {
                updateRealTimeMetrics(payload.data as Record<string, unknown>);
              }
              break;

            case 'log': {
              const mapped = mapLogMessage(payload);
              if (mapped) {
                addLogEntry(mapped);
              }
              break;
            }

            case 'system_health':
            case 'health': {
              const healthPayload = payload.data as SystemHealth | undefined;
              if (healthPayload) {
                updateSystemHealth(healthPayload);
              }
              break;
            }

            case 'error':
              setConnectionStatus(false, payload.data?.error ?? '监控通道错误');
              break;

            case 'pong':
              break;

            default:
              console.debug('Unhandled WebSocket message type:', payload.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      // 连接关闭
      newSocket.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setState(prev => ({
          ...prev,
          isConnected: false,
          error: event.reason || `连接关闭 (code: ${event.code})`
        }));
        setConnectionStatus(false, event.reason || '连接已关闭');

        // 如果不是主动关闭，尝试重连
        if (shouldReconnect.current && state.reconnectCount < reconnectAttempts) {
          scheduleReconnect();
        }
      };

      // 连接错误
      newSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        const errorMessage = '连接失败';
        setState(prev => ({
          ...prev,
          error: errorMessage,
          isConnected: false
        }));
        setConnectionStatus(false, errorMessage);
      };

      setState(prev => ({ ...prev, socket: newSocket }));
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setState(prev => ({
        ...prev,
        error: '创建 WebSocket 连接失败'
      }));
    }
  }, [url, state.socket, state.reconnectCount, reconnectAttempts, reconnectDelay, addLogEntry, mapLogMessage, setConnectionStatus, updateRealTimeMetrics, updateSystemHealth]);

  const disconnect = useCallback(() => {
    shouldReconnect.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (state.socket) {
      state.socket.close();
      setState(prev => ({
        ...prev,
        socket: null,
        isConnected: false,
        error: null
      }));
      setConnectionStatus(false);
    }
  }, [state.socket, setConnectionStatus]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    setState(prev => ({
      ...prev,
      reconnectCount: prev.reconnectCount + 1
    }));

    console.log(`Scheduling reconnect attempt ${state.reconnectCount + 1}/${reconnectAttempts} in ${reconnectDelay}ms`);

    reconnectTimeoutRef.current = setTimeout(() => {
      if (state.reconnectCount < reconnectAttempts) {
        connect();
      } else {
        setState(prev => ({
          ...prev,
          error: `重连失败，已达到最大重试次数 (${reconnectAttempts})`
        }));
      }
    }, reconnectDelay);
  }, [state.reconnectCount, reconnectAttempts, reconnectDelay, connect]);

  const sendMessage = useCallback((event: string, data?: unknown) => {
    if (state.socket?.readyState === WebSocket.OPEN) {
      const message = data
        ? JSON.stringify({ action: event, data })
        : JSON.stringify({ action: event });
      state.socket.send(message);
      return true;
    }
    console.warn('Cannot send message: socket not connected');
    return false;
  }, [state.socket]);

  // 订阅特定事件（简化版，原生 WebSocket 没有事件系统）
  const subscribe = useCallback((event: string, _callback: (...args: unknown[]) => void) => {
    console.log('Subscribe called for event:', event);
    // 原生 WebSocket 不支持事件订阅，这里只是保持 API 兼容性
    return () => {};
  }, []);

  // 初始化连接
  useEffect(() => {
    if (autoConnect) {
      shouldReconnect.current = true;
      connect();
    }

    return () => {
      shouldReconnect.current = false;
      disconnect();
    };
  }, [autoConnect]); // eslint-disable-line react-hooks/exhaustive-deps

  // 清理定时器
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    reconnect: () => {
      disconnect();
      setTimeout(() => {
        shouldReconnect.current = true;
        connect();
      }, 1000);
    }
  };
}
