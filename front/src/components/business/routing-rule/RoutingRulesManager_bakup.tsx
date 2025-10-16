'use client';

import React, { Suspense, use, useActionState } from 'react';
import { Card, Row, Col, Button, Badge, Tag, Modal, Form, Input, Select, Switch, Alert, Divider, Steps, Descriptions } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  BranchesOutlined,
  ApiOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

interface RoutingRule {
  id: string;
  name: string;
  description: string;
  priority: number;
  status: 'active' | 'inactive' | 'testing';
  // 多协议接入配置
  sourceConfig: {
    protocols: Array<'UDP' | 'HTTP' | 'WebSocket' | 'MQTT' | 'TCP'>;
    pattern: string;
    ports?: number[];
    topics?: string[]; // MQTT专用
    endpoints?: string[]; // HTTP专用
  };
  // 数据处理管道配置
  pipeline: {
    parser: {
      type: 'json' | 'xml' | 'binary' | 'text' | 'custom';
      schema?: string;
    };
    validator: {
      enabled: boolean;
      rules: string[];
    };
    transformer: {
      enabled: boolean;
      mappings: DataTransform[];
    };
  };
  // 目标系统配置
  targetSystems: TargetSystemConfig[];
  conditions: RuleCondition[];
  stats: {
    matchCount: number;
    successRate: number;
    avgProcessingTime: number;
    protocolStats: Record<string, number>;
  };
  createdAt: string;
  lastUpdated: string;
}

interface TargetSystemConfig {
  id: string;
  name: string;
  protocol: 'HTTP' | 'UDP' | 'MQTT' | 'WebSocket' | 'TCP';
  endpoint: string;
  port?: number;
  topic?: string; // MQTT专用
  headers?: Record<string, string>; // HTTP专用
  timeout: number;
  retryPolicy: {
    maxRetries: number;
    retryDelay: number;
  };
}

interface RuleCondition {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'regex' | 'gt' | 'lt';
  value: string;
  logicalOperator?: 'AND' | 'OR';
}

interface DataTransform {
  type: 'map' | 'filter' | 'rename' | 'format' | 'calculate';
  source: string;
  target: string;
  expression?: string;
}

// 模拟获取路由规则列表
async function fetchRoutingRules(): Promise<RoutingRule[]> {
  await new Promise(resolve => setTimeout(resolve, 1200));

  return [
    {
      id: '1',
      name: '用户数据统一路由',
      description: '多协议接收用户数据，统一处理后分发到用户系统和分析系统',
      priority: 1,
      status: 'active',
      sourceConfig: {
        protocols: ['HTTP', 'WebSocket', 'MQTT'],
        pattern: 'user.*',
        endpoints: ['/api/user/*'],
        topics: ['user/events', 'user/actions']
      },
      pipeline: {
        parser: {
          type: 'json',
          schema: 'user-event-schema.json'
        },
        validator: {
          enabled: true,
          rules: ['required:user_id', 'type:object']
        },
        transformer: {
          enabled: true,
          mappings: [
            { type: 'map', source: 'user_id', target: 'userId' },
            { type: 'format', source: 'timestamp', target: 'timestamp', expression: 'ISO8601' }
          ]
        }
      },
      targetSystems: [
        {
          id: 'user-db',
          name: '用户数据库',
          protocol: 'HTTP',
          endpoint: 'http://user-service:8080/api/events',
          timeout: 5000,
          headers: { 'Content-Type': 'application/json' },
          retryPolicy: { maxRetries: 3, retryDelay: 1000 }
        },
        {
          id: 'analytics',
          name: '分析系统',
          protocol: 'MQTT',
          endpoint: 'analytics.mqtt.broker',
          topic: 'analytics/user-events',
          timeout: 3000,
          retryPolicy: { maxRetries: 2, retryDelay: 500 }
        }
      ],
      conditions: [
        { field: 'type', operator: 'equals', value: 'user_event' },
        { field: 'user_id', operator: 'gt', value: '0', logicalOperator: 'AND' }
      ],
      stats: {
        matchCount: 15420,
        successRate: 98.7,
        avgProcessingTime: 12,
        protocolStats: { HTTP: 8500, WebSocket: 4200, MQTT: 2720 }
      },
      createdAt: '2024-01-15',
      lastUpdated: '2024-03-20'
    },
    {
      id: '2',
      name: '工控设备数据路由',
      description: 'UDP和TCP协议接收工控设备数据，转换后发送到监控和存储系统',
      priority: 0,
      status: 'active',
      sourceConfig: {
        protocols: ['UDP', 'TCP'],
        pattern: 'device.*',
        ports: [8001, 8005]
      },
      pipeline: {
        parser: {
          type: 'binary',
          schema: 'modbus-schema.bin'
        },
        validator: {
          enabled: true,
          rules: ['checksum:valid', 'length:min=8']
        },
        transformer: {
          enabled: true,
          mappings: [
            { type: 'calculate', source: 'raw_value', target: 'scaled_value', expression: 'raw_value * 0.1' },
            { type: 'map', source: 'device_addr', target: 'deviceId' }
          ]
        }
      },
      targetSystems: [
        {
          id: 'scada',
          name: 'SCADA监控系统',
          protocol: 'UDP',
          endpoint: '192.168.1.100',
          port: 9001,
          timeout: 2000,
          retryPolicy: { maxRetries: 5, retryDelay: 200 }
        },
        {
          id: 'historian',
          name: '历史数据库',
          protocol: 'HTTP',
          endpoint: 'http://historian:8080/api/data',
          timeout: 10000,
          retryPolicy: { maxRetries: 3, retryDelay: 1000 }
        }
      ],
      conditions: [
        { field: 'device_type', operator: 'equals', value: 'plc' },
        { field: 'data_quality', operator: 'equals', value: 'good', logicalOperator: 'AND' }
      ],
      stats: {
        matchCount: 8735,
        successRate: 99.8,
        avgProcessingTime: 5,
        protocolStats: { UDP: 6200, TCP: 2535 }
      },
      createdAt: '2024-02-01',
      lastUpdated: '2024-03-18'
    },
    {
      id: '3',
      name: '实时告警分发',
      description: '多协议接收告警信息，实时分发到告警系统和通知服务',
      priority: 0,
      status: 'testing',
      sourceConfig: {
        protocols: ['MQTT', 'HTTP', 'WebSocket'],
        pattern: 'alert.*|alarm.*',
        topics: ['alerts/critical', 'alerts/warning'],
        endpoints: ['/api/alerts/*']
      },
      pipeline: {
        parser: {
          type: 'json',
          schema: 'alert-schema.json'
        },
        validator: {
          enabled: true,
          rules: ['required:severity', 'enum:severity[critical,warning,info]']
        },
        transformer: {
          enabled: false,
          mappings: []
        }
      },
      targetSystems: [
        {
          id: 'alert-manager',
          name: '告警管理系统',
          protocol: 'HTTP',
          endpoint: 'http://alertmanager:9093/api/v1/alerts',
          timeout: 3000,
          retryPolicy: { maxRetries: 5, retryDelay: 1000 }
        },
        {
          id: 'notification',
          name: '通知服务',
          protocol: 'WebSocket',
          endpoint: 'ws://notification:8080/ws',
          timeout: 5000,
          retryPolicy: { maxRetries: 2, retryDelay: 500 }
        }
      ],
      conditions: [
        { field: 'severity', operator: 'equals', value: 'critical' },
        { field: 'source', operator: 'regex', value: '^(api|db|cache).*', logicalOperator: 'OR' }
      ],
      stats: {
        matchCount: 89,
        successRate: 100,
        avgProcessingTime: 3,
        protocolStats: { MQTT: 45, HTTP: 32, WebSocket: 12 }
      },
      createdAt: '2024-03-01',
      lastUpdated: '2024-03-19'
    }
  ];
}

// React 19 Action for creating routing rule
async function createRoutingRuleAction(_prevState: unknown, formData: FormData) {
  try {
    const name = formData.get('name') as string;
    // const _description = formData.get('description') as string;
    // const _sourcePattern = formData.get('sourcePattern') as string;
    // const _priority = parseInt(formData.get('priority') as string);
    // const _is_active = formData.get('is_active') === 'true';

    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000));

    if (Math.random() > 0.85) {
      throw new Error('路由规则冲突，请检查源模式');
    }

    return {
      success: true,
      error: null,
      message: `路由规则 "${name}" 创建成功`
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : '创建失败',
      message: null
    };
  }
}

// 使用React 19 use() Hook的规则列表组件
function RoutingRulesList({ rulesPromise, onViewDetail }: {
  rulesPromise: Promise<RoutingRule[]>;
  onViewDetail: (rule: RoutingRule) => void;
}) {
  const rules = use(rulesPromise);

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return { color: 'success', text: '运行中' };
      case 'inactive':
        return { color: 'default', text: '已停用' };
      case 'testing':
        return { color: 'processing', text: '测试中' };
      default:
        return { color: 'default', text: '未知' };
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority === 0) return 'red';
    if (priority <= 2) return 'orange';
    if (priority <= 5) return 'blue';
    return 'green';
  };

  const getProtocolIcon = (protocol: string) => {
    const iconMap = {
      'HTTP': '🌐',
      'WebSocket': '🔌',
      'MQTT': '📡',
      'UDP': '📨',
      'TCP': '🔗'
    };
    return iconMap[protocol as keyof typeof iconMap] || '🔧';
  };

  return (
    <div className="space-y-4">
      {rules.map((rule) => {
        const statusConfig = getStatusConfig(rule.status);

        return (
          <Card key={rule.id} className="hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-medium text-gray-900 cursor-pointer hover:text-blue-600"
                      onClick={() => onViewDetail(rule)}>
                    {rule.name}
                  </h3>
                  <Badge status={statusConfig.color as 'success' | 'error' | 'warning' | 'default'} text={statusConfig.text} />
                  <Tag color={getPriorityColor(rule.priority)}>
                    优先级 {rule.priority}
                  </Tag>
                </div>

                <p className="text-sm text-gray-600 mb-3">{rule.description}</p>

                {/* 协议接入配置 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">接入协议</div>
                    <div className="flex flex-wrap gap-1">
                      {rule.sourceConfig.protocols.map((protocol, index) => (
                        <Tag key={index} color="blue">
                          {getProtocolIcon(protocol)} {protocol}
                        </Tag>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs text-gray-500 mb-1">数据模式</div>
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {rule.sourceConfig.pattern}
                    </code>
                  </div>

                  <div>
                    <div className="text-xs text-gray-500 mb-1">处理管道</div>
                    <div className="flex gap-1">
                      <Tag color={rule.pipeline.parser.type === 'json' ? 'green' : 'orange'}>
                        解析: {rule.pipeline.parser.type.toUpperCase()}
                      </Tag>
                      <Tag color={rule.pipeline.validator.enabled ? 'green' : 'default'}>
                        验证: {rule.pipeline.validator.enabled ? '启用' : '禁用'}
                      </Tag>
                      <Tag color={rule.pipeline.transformer.enabled ? 'green' : 'default'}>
                        转换: {rule.pipeline.transformer.enabled ? '启用' : '禁用'}
                      </Tag>
                    </div>
                  </div>
                </div>

                {/* 目标系统配置 */}
                <div className="mb-4">
                  <div className="text-xs text-gray-500 mb-2">目标系统 ({rule.targetSystems.length})</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {rule.targetSystems.map((target, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded text-sm">
                        <span>{getProtocolIcon(target.protocol)}</span>
                        <div className="flex-1">
                          <div className="font-medium">{target.name}</div>
                          <div className="text-xs text-gray-500">
                            {target.protocol}: {target.endpoint}
                            {target.port && `:${target.port}`}
                            {target.topic && ` (${target.topic})`}
                          </div>
                        </div>
                        <Tag color="blue">{target.timeout}ms</Tag>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 协议统计 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">总处理量</div>
                    <div className="text-sm font-medium">{rule.stats.matchCount.toLocaleString()} 次</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">成功率</div>
                    <div className="text-sm font-medium text-green-600">{rule.stats.successRate}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">平均耗时</div>
                    <div className="text-sm font-medium">{rule.stats.avgProcessingTime}ms</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">协议分布</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(rule.stats.protocolStats).map(([protocol, count]) => (
                        <Tag key={protocol} color="purple">
                          {protocol}: {count}
                        </Tag>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="text-xs text-gray-500">
                  创建时间: {rule.createdAt} | 最后更新: {rule.lastUpdated}
                </div>
              </div>

              <div className="flex flex-col gap-2 ml-4">
                <Button
                  size="small"
                  icon={<BranchesOutlined />}
                  type="text"
                  title="查看详情"
                  onClick={() => onViewDetail(rule)}
                />
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  type="text"
                  title="编辑规则"
                />
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  type="text"
                  title="复制规则"
                />
                <Button
                  size="small"
                  icon={rule.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />}
                  type="text"
                  title={rule.status === 'active' ? '停用规则' : '启用规则'}
                />
                <Button
                  size="small"
                  icon={<DeleteOutlined />}
                  type="text"
                  danger
                  title="删除规则"
                />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// 数据处理管道可视化组件
function PipelineVisualization({ rule }: { rule: RoutingRule }) {
  const steps = [
    {
      title: '协议接入',
      description: rule.sourceConfig.protocols.join(', '),
      icon: <ApiOutlined />,
      status: 'finish' as const
    },
    {
      title: '数据解析',
      description: `${rule.pipeline.parser.type.toUpperCase()} 格式`,
      icon: <CheckCircleOutlined />,
      status: 'finish' as const
    },
    {
      title: '数据验证',
      description: rule.pipeline.validator.enabled ? `${rule.pipeline.validator.rules.length} 个规则` : '已跳过',
      icon: <CheckCircleOutlined />,
      status: (rule.pipeline.validator.enabled ? 'finish' : 'wait') as 'finish' | 'wait'
    },
    {
      title: '数据转换',
      description: rule.pipeline.transformer.enabled ? `${rule.pipeline.transformer.mappings.length} 个映射` : '已跳过',
      icon: <CheckCircleOutlined />,
      status: (rule.pipeline.transformer.enabled ? 'finish' : 'wait') as 'finish' | 'wait'
    },
    {
      title: '分发输出',
      description: `${rule.targetSystems.length} 个目标系统`,
      icon: <DatabaseOutlined />,
      status: 'finish' as const
    }
  ];

  return (
    <Card title="数据处理管道" size="small">
      <Steps
        items={steps}
        size="small"
        direction="horizontal"
        current={4}
      />
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div>
          <div className="font-medium mb-1">接入配置</div>
          <div className="text-gray-600">
            {rule.sourceConfig.endpoints && (
              <div>HTTP: {rule.sourceConfig.endpoints.join(', ')}</div>
            )}
            {rule.sourceConfig.topics && (
              <div>MQTT: {rule.sourceConfig.topics.join(', ')}</div>
            )}
            {rule.sourceConfig.ports && (
              <div>端口: {rule.sourceConfig.ports.join(', ')}</div>
            )}
          </div>
        </div>
        <div>
          <div className="font-medium mb-1">处理配置</div>
          <div className="text-gray-600">
            <div>解析器: {rule.pipeline.parser.type}</div>
            {rule.pipeline.parser.schema && (
              <div>模式: {rule.pipeline.parser.schema}</div>
            )}
          </div>
        </div>
        <div>
          <div className="font-medium mb-1">输出配置</div>
          <div className="text-gray-600">
            {rule.targetSystems.map((target, index) => (
              <div key={index}>{target.protocol}: {target.name}</div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

// 规则详情模态框
function RuleDetailModal({ rule, open, onClose }: {
  rule: RoutingRule | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!rule) return null;

  return (
    <Modal
      title={`路由规则详情 - ${rule.name}`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={1000}
      destroyOnClose
    >
      <div className="space-y-6">
        {/* 管道可视化 */}
        <PipelineVisualization rule={rule} />

        {/* 基本信息 */}
        <Card title="基本信息" size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="规则名称">{rule.name}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={rule.priority === 0 ? 'red' : rule.priority <= 2 ? 'orange' : 'blue'}>
                {rule.priority}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge
                status={rule.status === 'active' ? 'success' : rule.status === 'testing' ? 'processing' : 'default'}
                text={rule.status === 'active' ? '运行中' : rule.status === 'testing' ? '测试中' : '已停用'}
              />
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">{rule.createdAt}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{rule.description}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 条件规则 */}
        {rule.conditions.length > 0 && (
          <Card title="匹配条件" size="small">
            <div className="space-y-2">
              {rule.conditions.map((condition, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  {index > 0 && condition.logicalOperator && (
                    <Tag color="blue">{condition.logicalOperator}</Tag>
                  )}
                  <code className="bg-gray-100 px-2 py-1 rounded">
                    {condition.field} {condition.operator} &quot;{condition.value}&quot;
                  </code>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 性能统计 */}
        <Card title="性能统计" size="small">
          <Row gutter={16}>
            <Col span={6}>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{rule.stats.matchCount.toLocaleString()}</div>
                <div className="text-sm text-gray-500">总处理量</div>
              </div>
            </Col>
            <Col span={6}>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{rule.stats.successRate}%</div>
                <div className="text-sm text-gray-500">成功率</div>
              </div>
            </Col>
            <Col span={6}>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{rule.stats.avgProcessingTime}ms</div>
                <div className="text-sm text-gray-500">平均耗时</div>
              </div>
            </Col>
            <Col span={6}>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{rule.targetSystems.length}</div>
                <div className="text-sm text-gray-500">目标系统</div>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 规则测试 */}
        <RuleTestPanel rule={rule} />
      </div>
    </Modal>
  );
}

// 规则统计组件
function RuleStatistics({ rulesPromise }: { rulesPromise: Promise<RoutingRule[]> }) {
  const rules = use(rulesPromise);

  const stats = {
    total: rules.length,
    active: rules.filter(r => r.status === 'active').length,
    inactive: rules.filter(r => r.status === 'inactive').length,
    testing: rules.filter(r => r.status === 'testing').length,
    totalMatches: rules.reduce((acc, r) => acc + r.stats.matchCount, 0),
    avgSuccessRate: rules.reduce((acc, r) => acc + r.stats.successRate, 0) / rules.length
  };

  return (
    <Row gutter={16}>
      <Col xs={12} sm={6}>
        <Card className="text-center">
          <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
          <div className="text-sm text-gray-500">总规则数</div>
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card className="text-center">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-sm text-gray-500">运行中</div>
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card className="text-center">
          <div className="text-2xl font-bold text-orange-600">{stats.testing}</div>
          <div className="text-sm text-gray-500">测试中</div>
        </Card>
      </Col>
      <Col xs={12} sm={6}>
        <Card className="text-center">
          <div className="text-2xl font-bold text-purple-600">
            {stats.avgSuccessRate.toFixed(1)}%
          </div>
          <div className="text-sm text-gray-500">平均成功率</div>
        </Card>
      </Col>
    </Row>
  );
}

// 协议特定配置组件
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ProtocolSpecificConfig({ protocol, value, onChange }: {
  protocol: string;
  value: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  switch (protocol) {
    case 'HTTP':
      return (
        <div className="space-y-3">
          <Form.Item label="HTTP 方法">
            <Select
              mode="multiple"
              placeholder="选择HTTP方法"
              value={value?.methods || []}
              onChange={(methods) => onChange({ ...value, methods })}
            >
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
              <Select.Option value="PATCH">PATCH</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="路径模式">
            <Input
              placeholder="/api/users/*"
              value={(value as Record<string, unknown>)?.pathPattern as string}
              onChange={(e) => onChange({ ...value, pathPattern: e.target.value })}
            />
          </Form.Item>
          <Form.Item label="请求头过滤">
            <Input.TextArea
              placeholder="Content-Type: application/json"
              rows={2}
              value={(value as Record<string, unknown>)?.headerFilters as string}
              onChange={(e) => onChange({ ...value, headerFilters: e.target.value })}
            />
          </Form.Item>
        </div>
      );

    case 'MQTT':
      return (
        <div className="space-y-3">
          <Form.Item label="订阅主题">
            <Select
              mode="tags"
              placeholder="输入MQTT主题"
              value={value?.topics || []}
              onChange={(topics) => onChange({ ...value, topics })}
            />
          </Form.Item>
          <Form.Item label="QoS等级">
            <Select
              value={value?.qos || 0}
              onChange={(qos) => onChange({ ...value, qos })}
            >
              <Select.Option value={0}>0 - 最多一次</Select.Option>
              <Select.Option value={1}>1 - 至少一次</Select.Option>
              <Select.Option value={2}>2 - 恰好一次</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="保留消息">
            <Switch
              checked={(value as Record<string, unknown>)?.retain as boolean || false}
              onChange={(retain) => onChange({ ...value, retain })}
            />
          </Form.Item>
        </div>
      );

    case 'UDP':
      return (
        <div className="space-y-3">
          <Form.Item label="监听端口">
            <Input
              type="number"
              placeholder="8001"
              value={(value as Record<string, unknown>)?.port as number}
              onChange={(e) => onChange({ ...value, port: parseInt(e.target.value) })}
            />
          </Form.Item>
          <Form.Item label="缓冲区大小">
            <Select
              value={value?.bufferSize || 1024}
              onChange={(bufferSize) => onChange({ ...value, bufferSize })}
            >
              <Select.Option value={512}>512 字节</Select.Option>
              <Select.Option value={1024}>1KB</Select.Option>
              <Select.Option value={2048}>2KB</Select.Option>
              <Select.Option value={4096}>4KB</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="超时设置(ms)">
            <Input
              type="number"
              placeholder="5000"
              value={(value as Record<string, unknown>)?.timeout as number}
              onChange={(e) => onChange({ ...value, timeout: parseInt(e.target.value) })}
            />
          </Form.Item>
        </div>
      );

    case 'TCP':
      return (
        <div className="space-y-3">
          <Form.Item label="监听端口">
            <Input
              type="number"
              placeholder="8005"
              value={(value as Record<string, unknown>)?.port as number}
              onChange={(e) => onChange({ ...value, port: parseInt(e.target.value) })}
            />
          </Form.Item>
          <Form.Item label="连接池大小">
            <Input
              type="number"
              placeholder="100"
              value={(value as Record<string, unknown>)?.maxConnections as number}
              onChange={(e) => onChange({ ...value, maxConnections: parseInt(e.target.value) })}
            />
          </Form.Item>
          <Form.Item label="保活设置">
            <Switch
              checked={(value as Record<string, unknown>)?.keepAlive as boolean || false}
              onChange={(keepAlive) => onChange({ ...value, keepAlive })}
            />
          </Form.Item>
        </div>
      );

    case 'WebSocket':
      return (
        <div className="space-y-3">
          <Form.Item label="WebSocket路径">
            <Input
              placeholder="/ws"
              value={(value as Record<string, unknown>)?.path as string}
              onChange={(e) => onChange({ ...value, path: e.target.value })}
            />
          </Form.Item>
          <Form.Item label="子协议">
            <Select
              mode="tags"
              placeholder="输入子协议"
              value={value?.subProtocols || []}
              onChange={(subProtocols) => onChange({ ...value, subProtocols })}
            />
          </Form.Item>
          <Form.Item label="心跳间隔(秒)">
            <Input
              type="number"
              placeholder="30"
              value={(value as Record<string, unknown>)?.pingInterval as number}
              onChange={(e) => onChange({ ...value, pingInterval: parseInt(e.target.value) })}
            />
          </Form.Item>
        </div>
      );

    default:
      return (
        <Alert
          message="协议配置"
          description={`${protocol} 协议的特定配置选项将在后续版本中提供`}
          type="info"
          showIcon
        />
      );
  }
}

// 规则测试组件
function RuleTestPanel({ rule }: { rule: RoutingRule }) {
  const [testData, setTestData] = React.useState('{\n  "type": "user_event",\n  "user_id": 12345,\n  "action": "login"\n}');
  const [testResult, setTestResult] = React.useState<{
    matched?: boolean;
    processingTime?: number;
    error?: string;
    targetResults?: Array<{
      name: string;
      status: string;
      responseTime: number;
    }>;
  } | null>(null);
  const [testing, setTesting] = React.useState(false);

  const runTest = async () => {
    setTesting(true);
    try {
      // 模拟测试规则
      await new Promise(resolve => setTimeout(resolve, 2000));

      const mockResult = {
        matched: true,
        processingTime: Math.floor(Math.random() * 50) + 5,
        transformedData: JSON.parse(testData),
        targetResults: rule.targetSystems.map(target => ({
          name: target.name,
          status: Math.random() > 0.1 ? 'success' : 'failed',
          responseTime: Math.floor(Math.random() * 100) + 10
        }))
      };

      setTestResult(mockResult);
    } catch {
      setTestResult({ error: '测试数据格式错误' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card title="规则测试" size="small">
      <div className="space-y-4">
        <div>
          <div className="text-sm font-medium mb-2">测试数据</div>
          <Input.TextArea
            rows={6}
            value={testData}
            onChange={(e) => setTestData(e.target.value)}
            placeholder="输入测试数据"
          />
        </div>

        <div className="flex justify-end">
          <Button
            type="primary"
            loading={testing}
            onClick={runTest}
            disabled={!testData.trim()}
          >
            {testing ? '测试中...' : '运行测试'}
          </Button>
        </div>

        {testResult && (
          <div className="mt-4">
            <div className="text-sm font-medium mb-2">测试结果</div>
            {testResult.error ? (
              <Alert message="测试失败" description={testResult.error} type="error" />
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge status={testResult.matched ? "success" : "error"} />
                  <span className="text-sm">
                    规则匹配: {testResult.matched ? '成功' : '失败'}
                  </span>
                  <Tag color="blue">耗时: {testResult.processingTime}ms</Tag>
                </div>

                <div>
                  <div className="text-xs text-gray-500 mb-1">目标系统结果</div>
                  <div className="space-y-1">
                    {testResult.targetResults?.map((result, index: number) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                        <span>{result.name}</span>
                        <div className="flex items-center gap-2">
                          <Badge status={result.status === 'success' ? "success" : "error"} />
                          <span>{result.status === 'success' ? '成功' : '失败'}</span>
                          <Tag color="blue">{result.responseTime}ms</Tag>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
function CreateRoutingRuleModal({ open, onCancel }: { open: boolean; onCancel: () => void }) {
  const [state, formAction, isPending] = useActionState(createRoutingRuleAction, {
    success: false,
    error: null,
    message: null
  } as {
    success: boolean;
    error: string | null;
    message: string | null;
  });

  React.useEffect(() => {
    if ((state as { success: boolean }).success) {
      onCancel();
    }
  }, [state, onCancel]);

  return (
    <Modal
      title="创建路由规则"
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
      destroyOnHidden
    >
      {(state as { error: string | null }).error && (
        <Alert
          message="创建失败"
          description={(state as { error: string | null }).error}
          type="error"
          closable
          className="mb-4"
        />
      )}

      <form action={formAction}>
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="规则名称" required>
                <Input name="name" placeholder="输入路由规则名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="优先级" required>
                <Select placeholder="选择优先级" defaultValue="5">
                  <Select.Option value="0">0 - 最高 (紧急)</Select.Option>
                  <Select.Option value="1">1 - 高</Select.Option>
                  <Select.Option value="2">2 - 中</Select.Option>
                  <Select.Option value="3">3 - 正常</Select.Option>
                  <Select.Option value="4">4 - 低</Select.Option>
                  <Select.Option value="5">5 - 最低</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="规则描述">
            <Input.TextArea name="description" rows={2} placeholder="描述这个路由规则的用途" />
          </Form.Item>

          <Form.Item label="源数据模式" required>
            <Input
              name="sourcePattern"
              placeholder="例如: user.*, order.event.*, log.error.*"
              addonBefore="匹配模式:"
            />
          </Form.Item>

          <Divider orientation="left" plain>高级配置</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="匹配条件">
                <Input placeholder="field=value (后续版本支持可视化配置)" disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="数据转换">
                <Input placeholder="转换规则 (后续版本支持可视化配置)" disabled />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="启用状态">
            <Switch defaultChecked />
            <span className="ml-2 text-sm text-gray-500">创建后立即启用此规则</span>
          </Form.Item>

          <Form.Item className="mb-0 text-right">
            <Button onClick={onCancel} className="mr-2">
              取消
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={isPending}
              disabled={isPending}
            >
              {isPending ? '创建中...' : '创建规则'}
            </Button>
          </Form.Item>
        </Form>
      </form>
    </Modal>
  );
}

// 加载状态组件
function RulesLoadingFallback() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <Card key={i} loading className="h-48" />
      ))}
    </div>
  );
}

export function RoutingRulesManager() {
  const [rulesPromise, setRulesPromise] = React.useState<Promise<RoutingRule[]>>(
    () => fetchRoutingRules()
  );
  const [createModalOpen, setCreateModalOpen] = React.useState(false);
  const [detailModalOpen, setDetailModalOpen] = React.useState(false);
  const [selectedRule, setSelectedRule] = React.useState<RoutingRule | null>(null);

  const handleRefresh = () => {
    setRulesPromise(fetchRoutingRules());
  };

  const handleViewDetail = (rule: RoutingRule) => {
    setSelectedRule(rule);
    setDetailModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">路由规则管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            配置多协议数据路由规则，定义数据从源到目标的处理流程
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            icon={<BranchesOutlined />}
          >
            规则流程图
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            新建规则
          </Button>
        </div>
      </div>

      {/* 规则统计 */}
      <Suspense fallback={<Card loading />}>
        <RuleStatistics rulesPromise={rulesPromise} />
      </Suspense>

      {/* 路由规则列表 */}
      <Suspense fallback={<RulesLoadingFallback />}>
        <RoutingRulesList
          rulesPromise={rulesPromise}
          onViewDetail={handleViewDetail}
        />
      </Suspense>

      {/* 创建路由规则弹窗 */}
      <CreateRoutingRuleModal
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
      />

      {/* 规则详情弹窗 */}
      <RuleDetailModal
        rule={selectedRule}
        open={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedRule(null);
        }}
      />
    </div>
  );
}