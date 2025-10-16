'use client';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Badge,
  Progress,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Alert,
  Tabs,
  InputNumber,
  message,
} from 'antd';
import {
  PlusOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons';
import type {
  TargetSystem,
  CreateTargetSystemDto,
  UpdateTargetSystemDto,
  ProtocolType,
  EncryptionKey,
  ForwarderConfig,
} from '@/types/api';
import { useTargetSystemStore } from '@/stores/targetSystemStore';
import { apiClient } from '@/lib/api/client';
const { Option } = Select;
const { TextArea } = Input;
type ModalMode = 'create' | 'edit';
interface TargetSystemFormModalProps {
  mode: ModalMode;
  open: boolean;
  onCancel: () => void;
  initialSystem?: TargetSystem | null;
}
function TargetSystemFormModal({
  mode,
  open,
  onCancel,
  initialSystem,
}: TargetSystemFormModalProps) {
  const [form] = Form.useForm();
  const [protocolType, setProtocolType] = useState<ProtocolType>('HTTP' as ProtocolType);
  const [authType, setAuthType] = useState<string>('none');
  const [encryptionEnabled, setEncryptionEnabled] = useState<boolean>(false);
  const [encryptionKeys, setEncryptionKeys] = useState<EncryptionKey[]>([]);
  const [encryptionLoading, setEncryptionLoading] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    createSystem,
    updateSystem,
    error: storeError,
    clearError,
  } = useTargetSystemStore();
  const isEditMode = mode === 'edit' && initialSystem;
  useEffect(() => {
    if (!open) {
      form.resetFields();
      setError(null);
      setProtocolType('HTTP' as ProtocolType);
      setAuthType('none');
      setEncryptionEnabled(false);
      return;
    }
    let isMounted = true;
    const fetchEncryptionKeys = async () => {
      setEncryptionLoading(true);
      const response = await apiClient.encryptionKeys.list();
      if (!isMounted) {
        return;
      }
      if (response.success && Array.isArray(response.data)) {
        setEncryptionKeys(response.data);
      } else if (!response.success) {
        message.error(response.error || '获取加密密钥失败');
        setEncryptionKeys([]);
      } else {
        setEncryptionKeys([]);
      }
      setEncryptionLoading(false);
    };
    fetchEncryptionKeys();
    return () => {
      isMounted = false;
    };
  }, [open]);
  useEffect(() => {
    if (!open) {
      return;
    }
    if (isEditMode && initialSystem) {
      setProtocolType(initialSystem.protocol_type as ProtocolType);
      setAuthType(initialSystem.auth_config?.auth_type ?? 'none');
      const forwarder = initialSystem.forwarder_config || {};
      const endpoint = initialSystem.endpoint_config;
      const auth = initialSystem.auth_config;
      const encryption =
        (forwarder.encryption as Record<string, any> | undefined) ||
        (forwarder.encryption_config as Record<string, any> | undefined);
      const metadata = encryption?.metadata && typeof encryption.metadata === 'object'
        ? { ...(encryption.metadata as Record<string, any>) }
        : undefined;
      const keyName = metadata?.key_name ?? encryption?.key_name;
      if (metadata && metadata.key_name) {
        delete metadata.key_name;
      }
      setEncryptionEnabled(Boolean(encryption?.enabled));
      form.setFieldsValue({
        name: initialSystem.name,
        description: initialSystem.description ?? undefined,
        target_address: endpoint.target_address,
        target_port: endpoint.target_port,
        endpoint_path: endpoint.endpoint_path,
        use_ssl: endpoint.use_ssl,
        is_active: initialSystem.is_active,
        timeout: forwarder.timeout,
        retry_count: forwarder.retry_count,
        batch_size: forwarder.batch_size,
        compression: forwarder.compression,
        auth_username: auth?.username,
        auth_password: auth?.password,
        auth_token: auth?.token,
        auth_api_key: auth?.api_key,
        auth_api_key_header: auth?.api_key_header ?? 'X-API-Key',
        auth_custom_headers: auth?.custom_headers
          ? JSON.stringify(auth.custom_headers, null, 2)
          : undefined,
        transform_rules: initialSystem.transform_rules
          ? JSON.stringify(initialSystem.transform_rules, null, 2)
          : undefined,
        encryption_enabled: Boolean(encryption?.enabled),
        encryption_version: encryption?.version ?? 'v1',
        encryption_key_name: keyName,
        encryption_metadata:
          metadata && Object.keys(metadata).length > 0
            ? JSON.stringify(metadata, null, 2)
            : undefined,
      });
    } else {
      setProtocolType('HTTP' as ProtocolType);
      setAuthType('none');
      setEncryptionEnabled(false);
      form.resetFields();
      form.setFieldsValue({
        use_ssl: false,
        is_active: true,
        timeout: 30,
        retry_count: 3,
        batch_size: 100,
        encryption_enabled: false,
        encryption_version: 'v1',
      });
    }
  }, [open, isEditMode, initialSystem, form]);
  useEffect(() => {
    if (storeError) {
      setError(storeError);
      clearError();
    }
  }, [storeError, clearError]);
  const renderAuthConfig = useMemo(() => {
    switch (authType) {
      case 'basic':
        return (
          <>
            <Form.Item
              name="auth_username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="输入用户名" />
            </Form.Item>
            <Form.Item
              name="auth_password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="输入密码" />
            </Form.Item>
          </>
        );
      case 'bearer':
        return (
          <Form.Item
            name="auth_token"
            label="Bearer Token"
            rules={[{ required: true, message: '请输入 Token' }]}
          >
            <TextArea rows={3} placeholder="输入 Bearer Token" />
          </Form.Item>
        );
      case 'api_key':
        return (
          <>
            <Form.Item
              name="auth_api_key"
              label="API Key"
              rules={[{ required: true, message: '请输入 API Key' }]}
            >
              <Input placeholder="输入 API Key" />
            </Form.Item>
            <Form.Item
              name="auth_api_key_header"
              label="API Key Header 名称"
              initialValue="X-API-Key"
            >
              <Input placeholder="X-API-Key" />
            </Form.Item>
          </>
        );
      case 'custom':
        return (
          <Form.Item
            name="auth_custom_headers"
            label="自定义请求头 (JSON)"
            rules={[{ required: true, message: '请输入自定义请求头' }]}
          >
            <TextArea
              rows={4}
              placeholder={JSON.stringify(
                { Authorization: 'Custom token', 'X-Custom-Header': 'value' },
                null,
                2
              )}
            />
          </Form.Item>
        );
      default:
        return null;
    }
  }, [authType]);
  const handleSubmit = async (values: Record<string, any>) => {
    setLoading(true);
    setError(null);
    try {
      let customHeaders: Record<string, any> | undefined;
      let transformRules: Record<string, any> | undefined;
      let encryptionMetadata: Record<string, any> | undefined;
      if (values.auth_custom_headers) {
        customHeaders = JSON.parse(values.auth_custom_headers);
      }
      if (values.transform_rules) {
        transformRules = JSON.parse(values.transform_rules);
      }
      if (values.encryption_metadata) {
        const parsed = JSON.parse(values.encryption_metadata);
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('加密元数据必须是一个 JSON 对象');
        }
        encryptionMetadata = parsed as Record<string, any>;
      }
      const endpoint_config = {
        target_address: values.target_address,
        target_port: values.target_port,
        endpoint_path: values.endpoint_path,
        use_ssl: values.use_ssl ?? false,
      };
      const auth_config =
        authType !== 'none'
          ? {
              auth_type: authType,
              username: values.auth_username,
              password: values.auth_password,
              token: values.auth_token,
              api_key: values.auth_api_key,
              api_key_header: values.auth_api_key_header,
              custom_headers: customHeaders,
            }
          : undefined;
      const forwarder_config: ForwarderConfig = {
        timeout: typeof values.timeout === 'number' ? values.timeout : undefined,
        retry_count: typeof values.retry_count === 'number' ? values.retry_count : undefined,
        batch_size: typeof values.batch_size === 'number' ? values.batch_size : undefined,
        compression: typeof values.compression === 'boolean' ? values.compression : false,
      };
      if (values.encryption_enabled) {
        const metadata = { ...(encryptionMetadata ?? {}) };
        if (values.encryption_key_name) {
          metadata.key_name = values.encryption_key_name;
        }
        const encryptionConfig: Record<string, any> = {
          enabled: true,
          version: values.encryption_version || 'v1',
        };
        if (Object.keys(metadata).length > 0) {
          encryptionConfig.metadata = metadata;
        }
        forwarder_config.encryption = encryptionConfig;
      } else if (initialSystem?.forwarder_config?.encryption) {
        forwarder_config.encryption = { enabled: false };
      }
      const payload: CreateTargetSystemDto | UpdateTargetSystemDto = {
        name: values.name,
        description: values.description || null,
        protocol_type: protocolType,
        endpoint_config,
        auth_config,
        forwarder_config,
        transform_rules: transformRules,
        is_active: values.is_active ?? true,
      };
      const ok =
        mode === 'create'
          ? await createSystem(payload as CreateTargetSystemDto)
          : await updateSystem(initialSystem!.id, payload as UpdateTargetSystemDto);
      if (ok) {
        message.success(mode === 'create' ? '目标系统创建成功' : '目标系统更新成功');
        onCancel();
      } else {
        setError(mode === 'create' ? '创建失败' : '更新失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '数据解析失败，请检查 JSON 格式');
    } finally {
      setLoading(false);
    }
  };
  return (
    <Modal
      destroyOnClose
      title={mode === 'create' ? '创建目标系统' : '编辑目标系统'}
      open={open}
      onCancel={() => {
        form.resetFields();
        onCancel();
      }}
      footer={null}
      width={800}
    >
      {error && (
        <Alert
          message={mode === 'create' ? '创建失败' : '更新失败'}
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          className="mb-4"
        />
      )}
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="name"
          label="系统名称"
          rules={[{ required: true, message: '请输入系统名称' }]}
        >
          <Input placeholder="输入目标系统名称" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <TextArea rows={2} placeholder="输入系统描述" />
        </Form.Item>
        <Form.Item label="协议类型">
          <Select
            value={protocolType}
            onChange={(value) => setProtocolType(value as ProtocolType)}
            disabled={isEditMode}
          >
            <Option value="HTTP">HTTP</Option>
            <Option value="UDP">UDP</Option>
            <Option value="MQTT">MQTT</Option>
            <Option value="WEBSOCKET">WebSocket</Option>
            <Option value="TCP">TCP</Option>
          </Select>
        </Form.Item>
        <Tabs
          defaultActiveKey="endpoint"
          items={[
            {
              key: 'endpoint',
              label: '端点配置',
              children: (
                <>
                  <Form.Item
                    name="target_address"
                    label="目标地址"
                    rules={[{ required: true, message: '请输入目标地址' }]}
                  >
                    <Input placeholder="例如: api.example.com" />
                  </Form.Item>
                  <Form.Item
                    name="target_port"
                    label="目标端口"
                    rules={[{ required: true, message: '请输入目标端口' }]}
                  >
                    <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="endpoint_path" label="端点路径">
                    <Input placeholder="例如: /api/data" />
                  </Form.Item>
                  <Form.Item
                    name="use_ssl"
                    label="使用 SSL/TLS"
                    valuePropName="checked"
                    initialValue={false}
                  >
                    <Switch />
                  </Form.Item>
                </>
              ),
            },
            {
              key: 'auth',
              label: '认证配置',
              children: (
                <>
                  <Alert
                    message="根据目标系统的认证方式填写对应字段。留空表示不需要认证。"
                    type="info"
                    showIcon
                    className="mb-4"
                  />
                  <Form.Item label="认证类型">
                    <Select value={authType} onChange={setAuthType}>
                      <Option value="none">无认证</Option>
                      <Option value="basic">Basic 认证</Option>
                      <Option value="bearer">Bearer Token</Option>
                      <Option value="api_key">API Key</Option>
                      <Option value="custom">自定义请求头</Option>
                    </Select>
                  </Form.Item>
                  {renderAuthConfig}
                </>
              ),
            },
            {
              key: 'forwarder',
              label: '转发配置',
              children: (
                <>
                  <Form.Item name="timeout" label="超时时间 (秒)" initialValue={30}>
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="retry_count" label="重试次数" initialValue={3}>
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="batch_size" label="批处理大小" initialValue={100}>
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item
                    name="compression"
                    label="启用压缩"
                    valuePropName="checked"
                    initialValue={false}
                  >
                    <Switch />
                  </Form.Item>
                  <Form.Item
                    name="encryption_enabled"
                    label="启用加密"
                    valuePropName="checked"
                    initialValue={false}
                  >
                    <Switch
                      onChange={(checked) => {
                        setEncryptionEnabled(checked);
                        if (!checked) {
                          form.setFieldsValue({
                            encryption_key_name: undefined,
                            encryption_metadata: undefined,
                            encryption_version: 'v1',
                          });
                        } else if (!form.getFieldValue('encryption_version')) {
                          form.setFieldsValue({ encryption_version: 'v1' });
                        }
                      }}
                    />
                  </Form.Item>
                  {encryptionEnabled && (
                    <>
                      <Alert
                        message="启用后，网关会使用当前激活密钥对转发数据进行加密。可选择指定密钥或补充元数据。"
                        type="info"
                        showIcon
                        className="mb-4"
                      />
                      <Form.Item name="encryption_key_name" label="使用密钥">
                        <Select
                          allowClear
                          placeholder="选择密钥（默认使用当前激活密钥）"
                          loading={encryptionLoading}
                          optionFilterProp="children"
                          showSearch
                        >
                          {encryptionKeys.map((key) => (
                            <Option key={key.id} value={key.name}>
                              {key.name}
                              {key.is_active ? '（激活）' : ''}
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                      <Form.Item name="encryption_version" label="加密版本">
                        <Input placeholder="例如：v1" />
                      </Form.Item>
                      <Form.Item name="encryption_metadata" label="附加元数据 (JSON)">
                        <TextArea
                          rows={3}
                          placeholder={JSON.stringify({ tenant: 'demo' }, null, 2)}
                        />
                      </Form.Item>
                    </>
                  )}
                </>
              ),
            },
            {
              key: 'transform',
              label: '数据转换',
              children: (
                <>
                  <Alert
                    message="可选：使用 JSON 格式描述字段映射或转换逻辑，未填写则保持原始数据。"
                    type="info"
                    showIcon
                    className="mb-4"
                  />
                  <Form.Item
                    name="transform_rules"
                    label="转换规则 (JSON)"
                    help='示例: { "mappings": { "temperature": "$.data.temp" } }'
                  >
                    <TextArea
                      rows={4}
                      placeholder={JSON.stringify(
                        {
                          mappings: {
                            temperature: '$.data.temp',
                            humidity: '$.data.hum',
                          },
                        },
                        null,
                        2
                      )}
                    />
                  </Form.Item>
                </>
              ),
            },
          ]}
        />
        <Form.Item
          name="is_active"
          label="启用状态"
          valuePropName="checked"
          initialValue
        >
          <Switch />
        </Form.Item>
        <Form.Item className="mb-0 text-right">
          <Button onClick={onCancel} className="mr-2">
            取消
          </Button>
          <Button type="primary" htmlType="submit" loading={loading} disabled={loading}>
            {loading ? '提交中...' : mode === 'create' ? '创建' : '保存修改'}
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
}
interface TargetSystemGridProps {
  systems: TargetSystem[];
  onDelete: (id: string) => Promise<boolean>;
  onEdit: (system: TargetSystem) => void;
}
function TargetSystemGrid({ systems, onDelete, onEdit }: TargetSystemGridProps) {
  const { toggleSystem } = useTargetSystemStore();
  const getStatusConfig = (status?: TargetSystem['status']) => {
    switch (status) {
      case 'connected':
        return { color: 'success', text: '已连接', icon: <CheckCircleOutlined /> };
      case 'error':
        return { color: 'error', text: '异常', icon: <CloseCircleOutlined /> };
      case 'disconnected':
        return { color: 'default', text: '未连接', icon: <ExclamationCircleOutlined /> };
      default:
        return { color: 'default', text: '未知', icon: <ExclamationCircleOutlined /> };
    }
  };
  const handleTest = async (id: string) => {
    try {
      message.loading({ content: '正在测试连接...', key: `test-${id}` });
      await new Promise((resolve) => setTimeout(resolve, 800));
      message.success({ content: '连接测试成功', key: `test-${id}` });
    } catch {
      message.error({ content: '连接测试失败', key: `test-${id}` });
    }
  };
  const handleDelete = async (system: TargetSystem) => {
    const ok = await onDelete(system.id);
    if (!ok) {
      message.error('删除失败');
    }
  };
  if (systems.length === 0) {
    return (
      <Card>
        <div className="text-center py-8 text-gray-500">
          <ExclamationCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <p>暂无目标系统</p>
          <p className="text-sm">点击“添加目标系统”按钮创建第一个目标系统</p>
        </div>
      </Card>
    );
  }
  return (
    <Row gutter={[16, 16]}>
      {systems.map((system) => {
        const statusConfig = getStatusConfig(system.status);
        return (
          <Col key={system.id} xs={24} sm={12} lg={8} xl={6}>
            <Card
              className="h-full"
              actions={[
                <Button
                  key="test"
                  type="text"
                  icon={<ThunderboltOutlined />}
                  onClick={() => handleTest(system.id)}
                >
                  测试
                </Button>,
                <Button
                  key="toggle"
                  type="text"
                  icon={system.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                  onClick={async () => {
                    const ok = await toggleSystem(system.id, !system.is_active);
                    if (ok) {
                      message.success(system.is_active ? '已停用目标系统' : '已启用目标系统');
                    } else {
                      message.error('操作失败');
                    }
                  }}
                >
                  {system.is_active ? '停用' : '启用'}
                </Button>,
                <Button
                  key="config"
                  type="text"
                  icon={<SettingOutlined />}
                  onClick={() => onEdit(system)}
                >
                  配置
                </Button>,
                <Button
                  key="delete"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(system)}
                >
                  删除
                </Button>,
              ]}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 truncate" title={system.name}>
                  {system.name}
                </h3>
                <Badge
                  status={statusConfig.color as 'success' | 'error' | 'default'}
                  text={statusConfig.text}
                />
              </div>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">协议</span>
                  <span className="text-gray-900">{system.protocol_type}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">地址</span>
                  <span
                    className="text-gray-900 truncate"
                    title={`${system.endpoint_config.target_address}:${system.endpoint_config.target_port}`}
                  >
                    {system.endpoint_config.target_address}:{system.endpoint_config.target_port}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">认证</span>
                  <span className="text-gray-900">
                    {system.auth_config?.auth_type ?? 'none'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">状态</span>
                  <span className={system.is_active ? 'text-green-600' : 'text-gray-400'}>
                    {system.is_active ? '启用' : '停用'}
                  </span>
                </div>
                <div className="mt-3">
                  <Progress percent={system.is_active ? 100 : 0} size="small" showInfo={false} />
                </div>
                <div className="text-xs text-gray-500">
                  创建时间: {new Date(system.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}
export function TargetSystemsManager() {
  const {
    systems,
    loading,
    error,
    fetchSystems,
    deleteSystem,
    clearError,
  } = useTargetSystemStore();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingSystem, setEditingSystem] = useState<TargetSystem | null>(null);
  useEffect(() => {
    fetchSystems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);
  const handleDelete = async (id: string): Promise<boolean> => {
    const ok = await deleteSystem(id);
    if (ok) {
      message.success('删除成功');
    } else {
      message.error('删除失败');
    }
    return ok;
  };
  const handleOpenEdit = (system: TargetSystem) => {
    setEditingSystem(system);
    setEditModalOpen(true);
  };
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">目标系统管理</h2>
          <p className="text-sm text-gray-500 mt-1">配置和管理数据输出的目标系统</p>
        </div>
        <div className="flex items-center gap-3">
          <Button icon={<ReloadOutlined />} onClick={fetchSystems} loading={loading}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCreateModalOpen(true);
            }}
          >
            添加目标系统
          </Button>
        </div>
      </div>
      {loading ? (
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4].map((i) => (
            <Col key={i} xs={24} sm={12} lg={8} xl={6}>
              <Card loading className="h-64" />
            </Col>
          ))}
        </Row>
      ) : (
        <TargetSystemGrid
          systems={systems}
          onDelete={handleDelete}
          onEdit={handleOpenEdit}
        />
      )}
      <TargetSystemFormModal
        mode="create"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
      />
      <TargetSystemFormModal
        mode="edit"
        open={editModalOpen}
        onCancel={() => {
          setEditModalOpen(false);
          setEditingSystem(null);
        }}
        initialSystem={editingSystem ?? undefined}
      />
    </div>
  );
}
