'use client';

import React from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

export interface HealthTrendPoint {
  timestamp: string;
  cpu: number;
  memory: number;
  messageRate?: number;
  errorRate?: number;
}

interface HealthTrendChartProps {
  data: HealthTrendPoint[];
  height?: number;
}

export function HealthTrendChart({ data, height = 280 }: HealthTrendChartProps) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 16, right: 24, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickLine={false} />
          <YAxis
            yAxisId="left"
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickLine={false}
            tickFormatter={(value) => `${value}`}
          />
          <Tooltip
            formatter={(value, name) => {
              if (name === 'messageRate') {
                return [`${Number(value).toFixed(0)} 条/秒`, '消息速率'];
              }
              if (name === 'errorRate') {
                return [`${Number(value).toFixed(2)}%`, '错误率'];
              }
              return [`${Number(value).toFixed(0)}%`, name === 'cpu' ? 'CPU 利用率' : '内存利用率'];
            }}
          />
          <Legend />
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="cpu"
            name="CPU 利用率"
            stroke="#1890ff"
            fill="rgba(24,144,255,0.2)"
            strokeWidth={2}
            activeDot={{ r: 4 }}
          />
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="memory"
            name="内存利用率"
            stroke="#13c2c2"
            fill="rgba(19,194,194,0.18)"
            strokeWidth={2}
            activeDot={{ r: 4 }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="messageRate"
            name="消息速率"
            stroke="#722ed1"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="errorRate"
            name="错误率"
            stroke="#f5222d"
            strokeDasharray="4 4"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
