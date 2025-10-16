'use client';

import React, { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Select, Switch, Button, Card, Space, Alert, Row, Col, Tag, Divider } from 'antd';
import { PlusOutlined, MinusCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { TargetSystem, DataSource } from '@/types/api';

const { TextArea } = Input;
const { Option } = Select;

interface RoutingRuleFormSimpleProps {
  targetSystems: TargetSystem[];
  dataSources: DataSource[];
  onSubmit: (values: any) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  initialValues?: any;
}

// 协议类型选项
const PROTOCOL_OPTIONS = ['HTTP', 'UDP', 'TCP', 'MQTT', 'WEBSOCKET'];

// 条件操作符选项
const OPERATOR_OPTIONS = [
  { label: '等于 (=)', value: 'equals' },
  { label: '不等于 (≠)', value: 'not_equals' },
  { label: '包含', value: 'contains' },
  { label: '不包含', value: 'not_contains' },
  { label: '大于 (>)', value: 'greater_than' },
  { label: '小于 (<)', value: 'less_than' },
  { label: '大于等于 (≥)', value: 'greater_or_equal' },
  { label: '小于等于 (≤)', value: 'less_or_equal' },
  { label: '正则匹配', value: 'regex' },
  { label: '存在', value: 'exists' },
];

// 解析器类型选项
const PARSER_TYPE_OPTIONS = [
  { label: 'JSON 解析', value: 'json' },
  { label: 'XML 解析', value: 'xml' },
  { label: '文本解析', value: 'text' },
  { label: '二进制解析', value: 'binary' },
  { label: 'Modbus 解析', value: 'modbus' },
  { label: '自定义解析', value: 'custom' },
];

export function RoutingRuleFormSimple({
  targetSystems,
  dataSources,
  onSubmit,
  onCancel,
  loading = false,
  initialValues
}: RoutingRuleFormSimpleProps) {
  const [form] = Form.useForm();
  const [useAdvancedConfig, setUseAdvancedConfig] = useState(false);
  const [selectedProtocols, setSelectedProtocols] = useState<string[]>([]);

  useEffect(() => {
    if (initialValues) {
      form.resetFields();
      form.setFieldsValue(initialValues);
      setSelectedProtocols(initialValues.protocols || []);
      setUseAdvancedConfig(Boolean(initialValues.conditions && initialValues.conditions.length));
    } else {
      setSelectedProtocols([]);
      setUseAdvancedConfig(false);
    }
  }, [initialValues, form]);

  const handleFinish = async (values: any) => {
    // 构建 source_config
    const source_config: any = {};

    if (values.protocols && values.protocols.length > 0) {
      source_config.protocols = values.protocols;
    }

    if (values.data_source_ids && values.data_source_ids.length > 0) {
      source_config.data_source_ids = values.data_source_ids;
    }

    if (values.source_pattern) {
      source_config.pattern = values.source_pattern;
    }

    // 构建 pipeline
    const pipeline: any = {};

    if (values.parser_type) {
      pipeline.parser = {
        type: values.parser_type,
        options: values.parser_options ? JSON.parse(values.parser_options) : {}
      };
    }

    if (values.enable_validator) {
      pipeline.validator = {
        enabled: true,
        rules: values.validation_rules || []
      };
    }

    if (values.enable_transformer) {
      pipeline.transformer = {
        enabled: true,
        rules: values.transformation_rules || []
      };
    }

    // 构建 target_systems
    const target_systems = values.target_system_ids.map((id: string) => ({
      id,
      enabled: true,
    }));

    // 构建 conditions（高级模式）
    let conditions = undefined;
    if (useAdvancedConfig && values.conditions && values.conditions.length > 0) {
      conditions = values.conditions.map((cond: any) => ({
        field: cond.field,
        operator: cond.operator,
        value: cond.value
      }));
    }

    const payload = {
      name: values.name,
      description: values.description || '',
      priority: values.priority ?? 5,
      source_config,
      pipeline,
      target_systems,
      conditions,
      logical_operator: values.logical_operator || 'AND',
      is_active: values.is_active ?? true,
      is_published: values.is_published ?? false,
    };

    await onSubmit(payload);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleFinish}
      initialValues={{
        priority: 5,
        is_active: true,
        is_published: false,
        logical_operator: 'AND',
        enable_validator: false,
        enable_transformer: false,
      }}
    >
      <Card title="基本信息" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={16}>
            <Form.Item
              name="name"
              label="规则名称"
              rules={[{ required: true, message: '请输入规则名称' }]}
            >
              <Input placeholder="例如: HTTP请求转发到MQTT" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="priority"
              label="优先级"
              tooltip="数字越小，优先级越高（0-100）"
              rules={[{ required: true, message: '请输入优先级' }]}
            >
              <InputNumber
                min={0}
                max={100}
                style={{ width: '100%' }}
                placeholder="1-100"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="description"
          label="描述"
        >
          <TextArea rows={2} placeholder="描述这个路由规则的用途" />
        </Form.Item>
      </Card>

      <Card title="数据源匹配" size="small" className="mb-4">
        <Alert
          message="指定哪些数据源的数据会通过此路由规则"
          type="info"
          icon={<InfoCircleOutlined />}
          className="mb-4"
          showIcon
        />

        <Form.Item
          name="protocols"
          label="协议类型"
          tooltip="选择要匹配的协议类型"
        >
          <Select
            mode="multiple"
            placeholder="选择协议类型（留空表示所有协议）"
            onChange={setSelectedProtocols}
            allowClear
          >
            {PROTOCOL_OPTIONS.map(protocol => (
              <Option key={protocol} value={protocol}>{protocol}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="data_source_ids"
          label="指定数据源"
          tooltip="选择特定的数据源，留空表示匹配所有数据源"
        >
          <Select
            mode="multiple"
            placeholder="选择数据源（留空表示所有数据源）"
            showSearch
            filterOption={(input, option) =>
              (option?.label?.toString() || '').toLowerCase().includes(input.toLowerCase())
            }
            options={dataSources
              .filter(ds => selectedProtocols.length === 0 || selectedProtocols.includes(ds.protocol_type.toUpperCase()))
              .map(ds => ({
                label: `${ds.name} (${ds.protocol_type})`,
                value: ds.id,
              }))
            }
            allowClear
          />
        </Form.Item>

        <Form.Item
          name="source_pattern"
          label="消息模式匹配"
          tooltip="使用通配符匹配消息主题或路径，例如: user.*, order.event.*"
        >
          <Input placeholder="例如: user.*, order.*, sensor/temperature/*" />
        </Form.Item>
      </Card>

      <Card title="数据处理管道" size="small" className="mb-4">
        <Alert
          message="配置数据在路由过程中的处理流程"
          type="info"
          icon={<InfoCircleOutlined />}
          className="mb-4"
          showIcon
        />

        <Form.Item
          name="parser_type"
          label="解析器类型"
          tooltip="选择数据解析方式"
        >
          <Select placeholder="选择解析器（可选）" allowClear>
            {PARSER_TYPE_OPTIONS.map(parser => (
              <Option key={parser.value} value={parser.value}>{parser.label}</Option>
            ))}
          </Select>
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="enable_validator"
              label="启用数据验证"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="enable_transformer"
              label="启用数据转换"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>
      </Card>

      <Card title="目标系统" size="small" className="mb-4">
        <Alert
          message="选择数据转发的目标系统"
          type="info"
          icon={<InfoCircleOutlined />}
          className="mb-4"
          showIcon
        />

        <Form.Item
          name="target_system_ids"
          label="目标系统"
          rules={[{ required: true, message: '请选择至少一个目标系统' }]}
        >
          <Select
            mode="multiple"
            placeholder="选择一个或多个目标系统"
            showSearch
            filterOption={(input, option) =>
              (option?.label?.toString() || '').toLowerCase().includes(input.toLowerCase())
            }
            options={targetSystems.map(ts => ({
              label: (
                <span>
                  {ts.name}{' '}
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    {ts.protocol_type}
                  </Tag>
                  <span style={{ color: '#999', fontSize: 12 }}>
                    {ts.endpoint_config.target_address}:{ts.endpoint_config.target_port}
                  </span>
                </span>
              ),
              value: ts.id,
            }))}
          />
        </Form.Item>
      </Card>

      <Card
        title="高级配置"
        size="small"
        className="mb-4"
        extra={
          <Switch
            checked={useAdvancedConfig}
            onChange={setUseAdvancedConfig}
            checkedChildren="已启用"
            unCheckedChildren="已禁用"
          />
        }
      >
        {useAdvancedConfig && (
          <>
            <Alert
              message="配置高级匹配条件，用于更精细的数据过滤"
              type="info"
              icon={<InfoCircleOutlined />}
              className="mb-4"
              showIcon
            />

            <Form.Item
              name="logical_operator"
              label="逻辑运算符"
              tooltip="多个条件之间的逻辑关系"
            >
              <Select>
                <Option value="AND">AND（全部满足）</Option>
                <Option value="OR">OR（任一满足）</Option>
              </Select>
            </Form.Item>

            <Form.List name="conditions">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field, index) => (
                    <Card key={field.key} size="small" className="mb-2" type="inner">
                      <Row gutter={8}>
                        <Col span={8}>
                          <Form.Item
                            {...field}
                            name={[field.name, 'field']}
                            label={index === 0 ? "字段名" : undefined}
                            rules={[{ required: true, message: '请输入字段名' }]}
                          >
                            <Input placeholder="例如: type, status, temperature" />
                          </Form.Item>
                        </Col>
                        <Col span={7}>
                          <Form.Item
                            {...field}
                            name={[field.name, 'operator']}
                            label={index === 0 ? "操作符" : undefined}
                            rules={[{ required: true, message: '请选择操作符' }]}
                          >
                            <Select placeholder="选择操作符">
                              {OPERATOR_OPTIONS.map(op => (
                                <Option key={op.value} value={op.value}>{op.label}</Option>
                              ))}
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col span={7}>
                          <Form.Item
                            {...field}
                            name={[field.name, 'value']}
                            label={index === 0 ? "值" : undefined}
                            rules={[{ required: true, message: '请输入值' }]}
                          >
                            <Input placeholder="匹配值" />
                          </Form.Item>
                        </Col>
                        <Col span={2}>
                          {index === 0 && <div style={{ height: 30 }} />}
                          <Button
                            type="text"
                            danger
                            icon={<MinusCircleOutlined />}
                            onClick={() => remove(field.name)}
                          />
                        </Col>
                      </Row>
                    </Card>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    icon={<PlusOutlined />}
                    block
                  >
                    添加匹配条件
                  </Button>
                </>
              )}
            </Form.List>
          </>
        )}
      </Card>

      <Card title="状态设置" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="is_active"
              label="启用状态"
              valuePropName="checked"
              tooltip="禁用的规则不会被执行"
            >
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="is_published"
              label="发布状态"
              valuePropName="checked"
              tooltip="只有发布的规则才会生效"
            >
              <Switch checkedChildren="已发布" unCheckedChildren="未发布" />
            </Form.Item>
          </Col>
        </Row>
      </Card>

      <Divider />

      <Form.Item className="mb-0 text-right">
        <Space>
          <Button onClick={onCancel}>
            取消
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            disabled={loading}
          >
            {loading ? '提交中...' : '创建规则'}
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
}
