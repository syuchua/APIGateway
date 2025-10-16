'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface MetricLineChartProps {
  data: Array<{
    timestamp: string;
    value: number;
    rate?: number;
  }>;
  height?: number;
  dataKey?: string;
  stroke?: string;
  unit?: string;
}

export function MetricLineChart({
  data,
  height = 300,
  dataKey = 'value',
  stroke = '#1890ff',
  unit = ''
}: MetricLineChartProps) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip
            formatter={(value) => [value + unit, '数值']}
          />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={stroke}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}