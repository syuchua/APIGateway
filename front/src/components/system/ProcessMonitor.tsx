'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Card, Progress, Table, Tag } from 'antd';

type Proc = {
  pid: number;
  name: string;
  cpu: number;
  mem: number;
  updatedAt: number;
};

function genName(idx: number): string {
  const names = ['gateway', 'uvicorn', 'worker', 'forwarder', 'redis-client', 'db-conn', 'scheduler', 'ws-adapter'];
  return names[idx % names.length];
}

export function ProcessMonitor() {
  const [list, setList] = useState<Proc[]>(() =>
    new Array(8).fill(null).map((_, i) => ({
      pid: 1000 + i,
      name: genName(i),
      cpu: Math.round(Math.random() * 40) + (i === 0 ? 10 : 0),
      mem: Math.round(Math.random() * 40) + (i === 0 ? 10 : 0),
      updatedAt: Date.now(),
    }))
  );
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setList((prev) =>
        prev.map((p, idx) => {
          const jitter = (max: number) => Math.max(0, Math.min(100, Math.round(p.cpu + (Math.random() * max - max / 2))));
          const jitterMem = (max: number) => Math.max(0, Math.min(100, Math.round(p.mem + (Math.random() * max - max / 2))));
          const baseBoost = idx === 0 ? 5 : 0; // 主进程稍微更忙
          return {
            ...p,
            cpu: Math.min(100, Math.max(0, jitter(10) + baseBoost)),
            mem: Math.min(100, Math.max(0, jitterMem(6))),
            updatedAt: Date.now(),
          };
        })
      );
    }, 2000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  const columns = useMemo(
    () => [
      { title: 'PID', dataIndex: 'pid', key: 'pid', width: 80 },
      { title: '进程', dataIndex: 'name', key: 'name', width: 160, render: (v: string) => <code>{v}</code> },
      {
        title: 'CPU',
        dataIndex: 'cpu',
        key: 'cpu',
        render: (v: number) => (
          <div className="min-w-[140px]">
            <Progress percent={v} size="small" status={v > 85 ? 'exception' : v > 65 ? 'active' : 'normal'} />
          </div>
        ),
      },
      {
        title: '内存',
        dataIndex: 'mem',
        key: 'mem',
        render: (v: number) => (
          <div className="min-w-[140px]">
            <Progress percent={v} size="small" strokeColor="#13c2c2" />
          </div>
        ),
      },
      {
        title: '状态',
        dataIndex: 'updatedAt',
        key: 'status',
        width: 160,
        render: (t: number, record: Proc) => {
          const age = Math.max(0, Math.floor((Date.now() - t) / 1000));
          const busy = record.cpu > 85 || record.mem > 85;
          return (
            <div className="flex items-center gap-2">
              <Tag color={busy ? 'red' : 'green'}>{busy ? '繁忙' : '运行中'}</Tag>
              <span className="text-xs text-gray-500">{age}s前更新</span>
            </div>
          );
        },
      },
    ],
    []
  );

  return (
    <Card title="进程监视" extra={<span className="text-xs text-gray-500">仿 top 展示</span>}>
      <Table
        size="small"
        rowKey="pid"
        columns={columns as any}
        dataSource={list}
        pagination={false}
      />
    </Card>
  );
}

