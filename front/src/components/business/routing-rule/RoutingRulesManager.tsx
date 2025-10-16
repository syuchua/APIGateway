'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, Button, Badge, Tag, Modal, Alert, message, Descriptions } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CloudUploadOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/lib/api/client';
import type { RoutingRule, RoutingRuleSimple, TargetSystem, DataSource } from '@/types/api';
import { useRoutingRuleStore } from '@/stores/routingRuleStore';
import { RoutingRuleFormSimple } from './RoutingRuleFormSimple';

const mapRuleToFormValues = (rule: RoutingRule) => {
  const sourceConfig = (rule.source_config ?? {}) as Record<string, any>;
  const pipeline = (rule.pipeline ?? {}) as Record<string, any>;

  const parserOptions = pipeline.parser?.options;
  const parserOptionsString = parserOptions && Object.keys(parserOptions).length > 0
    ? JSON.stringify(parserOptions, null, 2)
    : undefined;

  const validationRules = pipeline.validator?.rules ?? [];
  const transformerRules = pipeline.transformer?.rules ?? [];

  const conditions = (rule.conditions ?? []).map((cond: any) => ({
    field: cond.field ?? cond.field_path ?? '',
    operator: cond.operator,
    value: cond.value,
  }));

  return {
    name: rule.name,
    description: rule.description ?? '',
    priority: rule.priority,
    is_active: rule.is_active,
    is_published: rule.is_published,
    protocols: (sourceConfig.protocols ?? []).map((p: string) => p.toUpperCase()),
    data_source_ids: sourceConfig.data_source_ids ?? [],
    source_pattern: sourceConfig.pattern ?? rule.source_pattern ?? '',
    parser_type: pipeline.parser?.type,
    parser_options: parserOptionsString,
    enable_validator: pipeline.validator?.enabled ?? validationRules.length > 0,
    validation_rules: validationRules,
    enable_transformer: pipeline.transformer?.enabled ?? transformerRules.length > 0,
    transformation_rules: transformerRules,
    target_system_ids: (rule.target_systems ?? []).map((ts) => ts.id),
    logical_operator: rule.logical_operator ?? 'AND',
    conditions,
  };
};

interface RoutingRuleFormModalProps {
  mode: 'create' | 'edit';
  open: boolean;
  onCancel: () => void;
  targetSystems: TargetSystem[];
  dataSources: DataSource[];
  initialRule?: RoutingRule;
}

function RoutingRuleFormModal({
  mode,
  open,
  onCancel,
  targetSystems,
  dataSources,
  initialRule,
}: RoutingRuleFormModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    createRule,
    updateRule,
    error: storeError,
    clearError,
  } = useRoutingRuleStore();

  useEffect(() => {
    if (storeError) {
      setError(storeError);
      clearError();
    }
  }, [storeError, clearError]);

  const initialValues = useMemo(() => {
    if (!initialRule) {
      return undefined;
    }
    return mapRuleToFormValues(initialRule);
  }, [initialRule]);

  const handleSubmit = async (payload: any) => {
    setSubmitting(true);
    setError(null);

    try {
      const ok = mode === 'create'
        ? await createRule(payload)
        : await updateRule(initialRule!.id, payload);

      if (ok) {
        message.success(mode === 'create' ? '路由规则创建成功' : '路由规则更新成功');
        onCancel();
      } else {
        setError(mode === 'create' ? '创建失败' : '更新失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误');
    } finally {
      setSubmitting(false);
    }
  };

  const modalTitle = mode === 'create' ? '创建路由规则' : '编辑路由规则';

  return (
    <Modal
      title={modalTitle}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={900}
      destroyOnClose
    >
      {error && (
        <Alert
          message={`${modalTitle}失败`}
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          className="mb-4"
        />
      )}

      <RoutingRuleFormSimple
        key={initialRule?.id ?? 'create'}
        targetSystems={targetSystems}
        dataSources={dataSources}
        onSubmit={handleSubmit}
        onCancel={onCancel}
        loading={submitting}
        initialValues={initialValues}
      />
    </Modal>
  );
}

// 规则详情模态框
function RuleDetailModal({
  rule,
  open,
  onClose
}: {
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
      width={900}
      destroyOnClose
    >
      <div className="space-y-4">
        <Card title="基本信息" size="small">
          <Descriptions column={2} size="small">
            <Descriptions.Item label="规则名称">{rule.name}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={rule.priority <= 2 ? 'red' : rule.priority <= 5 ? 'orange' : 'blue'}>
                {rule.priority}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge
                status={rule.is_active ? 'success' : 'default'}
                text={rule.is_active ? '已启用' : '已停用'}
              />
            </Descriptions.Item>
            <Descriptions.Item label="发布状态">
              <Badge
                status={rule.is_published ? 'success' : 'warning'}
                text={rule.is_published ? '已发布' : '未发布'}
              />
            </Descriptions.Item>
            <Descriptions.Item label="匹配次数">{rule.match_count || 0}</Descriptions.Item>
            <Descriptions.Item label="最后匹配">
              {rule.last_match_at ? new Date(rule.last_match_at).toLocaleString('zh-CN') : '从未匹配'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {new Date(rule.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            {rule.description && (
              <Descriptions.Item label="描述" span={2}>{rule.description}</Descriptions.Item>
            )}
          </Descriptions>
        </Card>

        <Card title="源配置" size="small">
          {rule.source_pattern && (
            <div className="mb-2">
              <span className="text-gray-500">源模式: </span>
              <code className="bg-gray-100 px-2 py-1 rounded">{rule.source_pattern}</code>
            </div>
          )}
          {rule.data_type_pattern && (
            <div className="mb-2">
              <span className="text-gray-500">数据类型: </span>
              <code className="bg-gray-100 px-2 py-1 rounded">{rule.data_type_pattern}</code>
            </div>
          )}
          <div>
            <span className="text-gray-500">详细配置: </span>
            <pre className="bg-gray-50 p-2 rounded mt-1 text-xs overflow-auto">
              {JSON.stringify(rule.source_config, null, 2)}
            </pre>
          </div>
        </Card>

        <Card title="处理管道" size="small">
          <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto">
            {JSON.stringify(rule.pipeline, null, 2)}
          </pre>
        </Card>

        <Card title="目标系统" size="small">
          <div className="space-y-2">
            {rule.target_systems.map((ts, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="font-medium">目标系统 ID: {ts.id}</span>
                <Badge
                  status={(ts as any).enabled !== false ? 'success' : 'default'}
                  text={(ts as any).enabled !== false ? '启用' : '停用'}
                />
              </div>
            ))}
          </div>
        </Card>

        {rule.conditions && (
          <Card title="匹配条件" size="small">
            <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto">
              {JSON.stringify(rule.conditions, null, 2)}
            </pre>
          </Card>
        )}
      </div>
    </Modal>
  );
}

// 路由规则列表组件
function RoutingRulesList({
  rules,
  onDelete,
  onViewDetail,
  onToggleActive,
  onTogglePublish,
  onReload,
  onEdit
}: {
  rules: RoutingRuleSimple[];
  onDelete: (id: string) => Promise<boolean>;
  onViewDetail: (id: string) => void;
  onToggleActive: (rule: RoutingRuleSimple) => Promise<void> | void;
  onTogglePublish: (rule: RoutingRuleSimple) => Promise<void> | void;
  onReload: (rule: RoutingRuleSimple) => Promise<void> | void;
  onEdit: (rule: RoutingRuleSimple) => void;
}) {
  const handleDelete = async (rule: RoutingRuleSimple) => {
    const ok = await onDelete(rule.id);
    if (!ok) {
      message.error('删除失败');
    }
  };

  if (rules.length === 0) {
    return (
      <Card>
        <div className="text-center py-8 text-gray-500">
          <BranchesOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <p>暂无路由规则</p>
          <p className="text-sm">点击"新建规则"按钮创建第一个路由规则</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {rules.map((rule) => (
        <Card key={rule.id} className="hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-lg font-medium text-gray-900">
                  {rule.name}
                </h3>
                <Badge
                  status={rule.is_active ? 'success' : 'default'}
                  text={rule.is_active ? '已启用' : '已停用'}
                />
                {rule.is_published ? (
                  <Tag color="green" icon={<CheckCircleOutlined />}>已发布</Tag>
                ) : (
                  <Tag color="orange" icon={<CloseCircleOutlined />}>未发布</Tag>
                )}
                <Tag color={rule.priority <= 2 ? 'red' : rule.priority <= 5 ? 'orange' : 'blue'}>
                  优先级 {rule.priority}
                </Tag>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                {rule.source_pattern && (
                  <div>
                    <div className="text-xs text-gray-500 mb-1">源模式</div>
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {rule.source_pattern}
                    </code>
                  </div>
                )}
                <div>
                  <div className="text-xs text-gray-500 mb-1">目标系统</div>
                  <div className="text-sm font-medium">{rule.target_system_ids.length} 个</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">匹配次数</div>
                  <div className="text-sm font-medium">{rule.match_count || 0} 次</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">最后匹配</div>
                  <div className="text-sm">
                    {rule.last_match_at
                      ? new Date(rule.last_match_at).toLocaleString('zh-CN', {
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : '从未'}
                  </div>
                </div>
              </div>

              <div className="text-xs text-gray-500">
                创建时间: {new Date(rule.created_at).toLocaleString('zh-CN')}
              </div>
            </div>

            <div className="flex flex-col gap-2 ml-4">
              <Button
                size="small"
                icon={<EyeOutlined />}
                type="text"
                title="查看详情"
                onClick={() => onViewDetail(rule.id)}
              />
              <Button
                size="small"
                icon={<EditOutlined />}
                type="text"
                title="编辑规则"
                onClick={() => onEdit(rule)}
              />
              <Button
                size="small"
                icon={rule.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                type="text"
                title={rule.is_active ? '停用规则' : '启用规则'}
                onClick={() => onToggleActive(rule)}
              />
              <Button
                size="small"
                icon={rule.is_published ? <CloudSyncOutlined /> : <CloudUploadOutlined />}
                type="text"
                title={rule.is_published ? '取消发布' : '发布规则'}
                onClick={() => onTogglePublish(rule)}
              />
              <Button
                size="small"
                icon={<ReloadOutlined />}
                type="text"
                title="重新加载到网关"
                onClick={() => onReload(rule)}
              />
              <Button
                size="small"
                icon={<DeleteOutlined />}
                type="text"
                danger
                title="删除规则"
                onClick={() => handleDelete(rule)}
              />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function RoutingRulesManager() {
  const {
    rules,
    loading: rulesLoading,
    error,
    fetchRules,
    deleteRule,
    toggleActive,
    togglePublish,
    reloadRule,
    fetchDetail,
    clearError
  } = useRoutingRuleStore();
  const [targetSystems, setTargetSystems] = useState<TargetSystem[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<RoutingRule | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<RoutingRule | null>(null);

  const fetchTargetSystems = async () => {
    try {
      const response = await apiClient.targetSystemsV2.list();
      if (response.success && response.data) {
        setTargetSystems(response.data.items || []);
      }
    } catch (error) {
      message.error('获取目标系统列表失败');
    }
  };

  const fetchDataSources = async () => {
    try {
      const response = await apiClient.dataSourcesV2.list();
      if (response.success && response.data) {
        setDataSources(response.data.items || []);
      }
    } catch (error) {
      message.error('获取数据源列表失败');
    }
  };

  const handleDelete = async (id: string): Promise<boolean> => {
    const ok = await deleteRule(id);
    if (ok) {
      message.success('删除成功');
    } else {
      message.error('删除失败');
    }
    return ok;
  };

  const handleToggleActive = async (rule: RoutingRuleSimple) => {
    const ok = await toggleActive(rule);
    if (ok) {
      message.success(rule.is_active ? '规则已停用' : '规则已启用');
    }
  };

  const handleTogglePublish = async (rule: RoutingRuleSimple) => {
    const ok = await togglePublish(rule);
    if (ok) {
      message.success(rule.is_published ? '已取消发布' : '发布成功');
    }
  };

  const handleReload = async (rule: RoutingRuleSimple) => {
    const ok = await reloadRule(rule.id);
    if (ok) {
      message.success('规则已重新加载到网关');
    }
  };

  const handleViewDetail = async (id: string) => {
    const detail = await fetchDetail(id);
    if (detail) {
      setSelectedRule(detail);
      setDetailModalOpen(true);
    }
  };

  const handleEdit = async (rule: RoutingRuleSimple) => {
    const detail = await fetchDetail(rule.id);
    if (detail) {
      setEditingRule(detail);
      setEditModalOpen(true);
    }
  };

  useEffect(() => {
    fetchRules();
    fetchTargetSystems();
    fetchDataSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (error) {
      message.error(error);
      clearError();
    }
  }, [error, clearError]);

  // 统计信息
  const stats = {
    total: rules.length,
    active: rules.filter(r => r.is_active).length,
    published: rules.filter(r => r.is_published).length,
    totalMatches: rules.reduce((acc, r) => acc + (r.match_count || 0), 0),
  };

  return (
    <div className="space-y-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">路由规则管理</h2>
          <p className="text-sm text-gray-500 mt-1">
            配置数据路由规则，定义数据从源到目标的处理流程
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchRules}
            loading={rulesLoading}
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

      {/* 统计卡片 */}
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
            <div className="text-sm text-gray-500">已启用</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="text-center">
            <div className="text-2xl font-bold text-purple-600">{stats.published}</div>
            <div className="text-sm text-gray-500">已发布</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="text-center">
            <div className="text-2xl font-bold text-orange-600">{stats.totalMatches.toLocaleString()}</div>
            <div className="text-sm text-gray-500">总匹配次数</div>
          </Card>
        </Col>
      </Row>

      {/* 路由规则列表 */}
      {rulesLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <Card key={i} loading className="h-32" />
          ))}
        </div>
      ) : (
        <RoutingRulesList
          rules={rules}
          onDelete={handleDelete}
          onViewDetail={handleViewDetail}
          onToggleActive={handleToggleActive}
          onTogglePublish={handleTogglePublish}
          onReload={handleReload}
          onEdit={handleEdit}
        />
      )}

      {/* 创建 / 编辑路由规则弹窗 */}
      <RoutingRuleFormModal
        mode="create"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        targetSystems={targetSystems}
        dataSources={dataSources}
      />

      <RoutingRuleFormModal
        mode="edit"
        open={editModalOpen}
        onCancel={() => {
          setEditModalOpen(false);
          setEditingRule(null);
        }}
        targetSystems={targetSystems}
        dataSources={dataSources}
        initialRule={editingRule ?? undefined}
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
