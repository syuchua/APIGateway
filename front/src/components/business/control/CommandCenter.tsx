'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Card, Row, Col, Select, Button, Table, Tag, Badge, message, Space, Alert } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '@/lib/api';
import type { DataSource, RoutingRuleSimple, TargetSystem } from '@/types/api';

type Granularity = 'global' | 'data-source' | 'target-system' | 'routing-rule';
type DsAction = 'start' | 'stop';
type TsAction = 'start' | 'stop';
type RuleAction = 'publish' | 'unpublish' | 'reload';

type CommandItem = {
  id: string;
  name: string;
  type: Granularity;
  action: string;
  status: 'PENDING' | 'SENT' | 'ACK_GATEWAY' | 'ACK_EXEC' | 'FAILED';
  detail?: string;
  startedAt: number;
  finishedAt?: number;
};

const statusBadge = (s: CommandItem['status']) => {
  const conf: Record<string, any> = {
    PENDING: { color: 'default', text: '待发送' },
    SENT: { color: 'processing', text: '已发送' },
    ACK_GATEWAY: { color: 'warning', text: '网关已确认' },
    ACK_EXEC: { color: 'success', text: '执行完成' },
    FAILED: { color: 'error', text: '失败' },
  };
  const c = conf[s] || conf.PENDING;
  return <Badge status={c.color} text={c.text} />;
};

export function CommandCenter() {
  const [granularity, setGranularity] = useState<Granularity>('data-source');
  const [dsAction, setDsAction] = useState<DsAction>('start');
  const [tsAction, setTsAction] = useState<TsAction>('start');
  const [ruleAction, setRuleAction] = useState<RuleAction>('publish');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [targets, setTargets] = useState<TargetSystem[]>([]);
  const [rules, setRules] = useState<RoutingRuleSimple[]>([]);
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [loading, setLoading] = useState(false);

  // load list data (simple pagination: first page 100)
  useEffect(() => {
    const load = async () => {
      const [ds, ts, rl] = await Promise.all([
        apiClient.dataSourcesV2.list({ page: 1, limit: 100 }),
        apiClient.targetSystemsV2.list({ page: 1, limit: 100 }),
        apiClient.routingRulesV2.listSimple({ page: 1, limit: 100 })
      ]);
      if (ds.success && ds.data) setDataSources(ds.data.items as any);
      if (ts.success && ts.data) setTargets(ts.data.items as any);
      if (rl.success && rl.data) setRules(rl.data.items as any);
    };
    load().catch(() => {});
  }, []);

  const targetOptions = useMemo(() => {
    switch (granularity) {
      case 'data-source':
        return dataSources.map(d => ({ label: `${d.name} (${d.protocol_type})`, value: d.id }));
      case 'target-system':
        return targets.map(t => ({ label: `${t.name} (${t.protocol_type})`, value: t.id }));
      case 'routing-rule':
        return rules.map(r => ({ label: `${r.name}`, value: r.id }));
      default:
        return [];
    }
  }, [granularity, dataSources, targets, rules]);

  const actionSelector = (
    <>
      {granularity === 'data-source' && (
        <Select value={dsAction} onChange={(v) => setDsAction(v)} options={[
          { label: '启动适配器', value: 'start' },
          { label: '停止适配器', value: 'stop' },
        ]} style={{ width: 160 }} />
      )}
      {granularity === 'target-system' && (
        <Select value={tsAction} onChange={(v) => setTsAction(v)} options={[
          { label: '启动转发', value: 'start' },
          { label: '停止转发', value: 'stop' },
        ]} style={{ width: 160 }} />
      )}
      {granularity === 'routing-rule' && (
        <Select value={ruleAction} onChange={(v) => setRuleAction(v)} options={[
          { label: '发布规则', value: 'publish' },
          { label: '下线规则', value: 'unpublish' },
          { label: '热更新', value: 'reload' },
        ]} style={{ width: 160 }} />
      )}
    </>
  );

  const columns: ColumnsType<CommandItem> = [
    { title: '对象', dataIndex: 'name', key: 'name', render: (text, r) => <span className="font-medium">{text}</span> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 120, render: (v) => ({'data-source':'数据源','target-system':'目标系统','routing-rule':'路由规则','global':'全局'}[v]) },
    { title: '指令', dataIndex: 'action', key: 'action', width: 120 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 140, render: (v) => statusBadge(v) },
    { title: '说明', dataIndex: 'detail', key: 'detail' },
  ];

  const enqueue = (items: CommandItem[]) => setCommands(prev => [...items, ...prev]);
  const updateStatus = (id: string, status: CommandItem['status'], detail?: string) =>
    setCommands(prev => prev.map(c => c.id === id ? { ...c, status, detail, finishedAt: status === 'ACK_EXEC' || status === 'FAILED' ? Date.now() : c.finishedAt } : c));

  const pollStatus = async (item: CommandItem) => {
    const deadline = Date.now() + 15_000;
    const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
    while (Date.now() < deadline) {
      try {
        if (item.type === 'data-source') {
          const s = await apiClient.dataSourcesV2.status(item.id);
          if (s.success && s.data) {
            const running = Boolean((s.data as any).is_running ?? (s.data as any).is_active);
            if ((item.action === 'start' && running) || (item.action === 'stop' && !running)) {
              updateStatus(item.id, 'ACK_EXEC', running ? '运行中' : '已停止');
              return;
            }
          }
        } else if (item.type === 'target-system') {
          const s = await apiClient.targetSystemsV2.status(item.id);
          if (s.success && s.data) {
            const status = String((s.data as any).status || '').toLowerCase();
            const running = ['running','started','ok','ready'].some(k => status.includes(k));
            if ((item.action === 'start' && running) || (item.action === 'stop' && !running)) {
              updateStatus(item.id, 'ACK_EXEC', running ? '运行中' : '已停止');
              return;
            }
          }
        } else if (item.type === 'routing-rule') {
          // 获取规则，校验发布状态；reload 直接视为完成
          if (item.action === 'reload') {
            updateStatus(item.id, 'ACK_EXEC', '热更新完成');
            return;
          }
          const r = await apiClient.routingRulesV2.get(item.id);
          if (r.success && r.data) {
            const published = Boolean((r.data as any).is_published);
            if ((item.action === 'publish' && published) || (item.action === 'unpublish' && !published)) {
              updateStatus(item.id, 'ACK_EXEC', published ? '已发布' : '未发布');
              return;
            }
          }
        }
      } catch {
        // ignore once
      }
      await sleep(1000);
    }
    updateStatus(item.id, 'FAILED', '超时未确认');
  };

  const send = async () => {
    if (granularity !== 'global' && selectedIds.length === 0) {
      message.warning('请至少选择一个对象');
      return;
    }
    setLoading(true);
    try {
      const now = Date.now();
      let items: CommandItem[] = [];
      if (granularity === 'data-source') {
        const dict = new Map(dataSources.map(d => [d.id, d] as const));
        items = selectedIds.map(id => ({ id, type: 'data-source', name: dict.get(id)?.name || id, action: dsAction, status: 'PENDING', startedAt: now }));
      } else if (granularity === 'target-system') {
        const dict = new Map(targets.map(t => [t.id, t] as const));
        items = selectedIds.map(id => ({ id, type: 'target-system', name: dict.get(id)?.name || id, action: tsAction, status: 'PENDING', startedAt: now }));
      } else if (granularity === 'routing-rule') {
        const dict = new Map(rules.map(r => [r.id, r] as const));
        items = selectedIds.map(id => ({ id, type: 'routing-rule', name: dict.get(id)?.name || id, action: ruleAction, status: 'PENDING', startedAt: now }));
      } else {
        items = [{ id: 'system', type: 'global', name: '系统', action: 'restart', status: 'PENDING', startedAt: now }];
      }
      enqueue(items);

      for (const it of items) {
        try {
          // 发起指令
          if (it.type === 'data-source') {
            const res = it.action === 'start' ? await apiClient.dataSourcesV2.start(it.id) : await apiClient.dataSourcesV2.stop(it.id);
            if (res.success) {
              updateStatus(it.id, 'ACK_GATEWAY', '已提交');
              pollStatus(it);
            } else {
              updateStatus(it.id, 'FAILED', res.error || '提交失败');
            }
          } else if (it.type === 'target-system') {
            const res = it.action === 'start' ? await apiClient.targetSystemsV2.start(it.id) : await apiClient.targetSystemsV2.stop(it.id);
            if (res.success) {
              updateStatus(it.id, 'ACK_GATEWAY', '已提交');
              pollStatus(it);
            } else {
              updateStatus(it.id, 'FAILED', res.error || '提交失败');
            }
          } else if (it.type === 'routing-rule') {
            let res;
            if (it.action === 'publish') res = await apiClient.routingRulesV2.publish(it.id);
            else if (it.action === 'unpublish') res = await apiClient.routingRulesV2.unpublish(it.id);
            else res = await apiClient.routingRulesV2.reload(it.id);
            if (res.success) {
              updateStatus(it.id, 'ACK_GATEWAY', '已提交');
              pollStatus(it);
            } else {
              updateStatus(it.id, 'FAILED', res.error || '提交失败');
            }
          } else {
            const res = await apiClient.system.restart();
            if (res.success) {
              updateStatus(it.id, 'ACK_GATEWAY', '网关将重启');
            } else {
              updateStatus(it.id, 'FAILED', res.error || '提交失败');
            }
          }
        } catch (e) {
          updateStatus(it.id, 'FAILED', e instanceof Error ? e.message : '网络错误');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">控制指令中心</h2>
          <p className="text-sm text-gray-500">按“颗粒度”下发指令，采用“握手确认”机制（提交确认 + 状态确认）</p>
        </div>
      </div>

      <Card>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Space direction="vertical" className="w-full">
              <div className="text-xs text-gray-500">颗粒度</div>
              <Select<Granularity>
                value={granularity}
                onChange={(v) => { setGranularity(v); setSelectedIds([]); }}
                options={[
                  { label: '数据源', value: 'data-source' },
                  { label: '目标系统', value: 'target-system' },
                  { label: '路由规则', value: 'routing-rule' },
                  { label: '全局', value: 'global' },
                ]}
                style={{ width: '100%' }}
              />
            </Space>
          </Col>

          <Col xs={24} sm={10} md={10}>
            <Space direction="vertical" className="w-full">
              <div className="text-xs text-gray-500">对象</div>
              {granularity === 'global' ? (
                <Alert type="info" showIcon message="全局操作将执行系统重启（仅提交确认）" />
              ) : (
                <Select
                  mode="multiple"
                  placeholder="选择对象"
                  value={selectedIds}
                  onChange={setSelectedIds}
                  options={targetOptions}
                  style={{ width: '100%' }}
                />
              )}
            </Space>
          </Col>

          <Col xs={24} sm={6} md={4}>
            <Space direction="vertical" className="w-full">
              <div className="text-xs text-gray-500">指令</div>
              {actionSelector}
            </Space>
          </Col>

          <Col xs={24} sm={24} md={4}>
            <Space className="w-full justify-end">
              <Button type="primary" onClick={send} loading={loading}>下发指令</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card title="握手确认结果">
        <Table
          rowKey={(r) => `${r.type}-${r.id}-${r.startedAt}`}
          size="small"
          columns={columns}
          dataSource={commands}
          pagination={{ pageSize: 8 }}
        />
        <div className="text-xs text-gray-500 mt-2">握手策略：1）HTTP返回=网关接收确认 2）状态轮询=执行确认（15秒超时）</div>
      </Card>
    </div>
  );
}

