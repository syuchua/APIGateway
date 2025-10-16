'use client';

import React, { useMemo } from 'react';
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

interface PerformanceBarChartProps {
  data: Array<{
    hour: string;
    throughput: number;
    latency: number;
    errorRate?: number;
  }>;
  height?: number;
  showErrorRate?: boolean;
}

const formatTooltip = (value: number, name: string) => {
  const unitMap: Record<string, string> = {
    throughput: ' MB/s',
    latency: ' ms',
    errorRate: ' %'
  };
  const labelMap: Record<string, string> = {
    throughput: '吞吐量',
    latency: '延迟',
    errorRate: '错误率'
  };

  return [`${value.toFixed(name === 'errorRate' ? 2 : 0)}${unitMap[name] ?? ''}`, labelMap[name] ?? name];
};

export function PerformanceBarChart({
  data,
  height = 320,
  showErrorRate = false
}: PerformanceBarChartProps) {
  const chartData = useMemo(
    () =>
      data.map((item) => ({
        ...item,
        errorRate: (item.errorRate ?? 0) * 100
      })),
    [data]
  );

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={chartData} margin={{ top: 16, right: 24, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="hour" tickLine={false} />
          <YAxis yAxisId="left" tickLine={false} />
          <YAxis yAxisId="right" orientation="right" tickLine={false} />
          <Tooltip formatter={formatTooltip} />
          <Legend />
          <Bar
            yAxisId="left"
            dataKey="throughput"
            name="吞吐量"
            fill="#1890ff"
            radius={[4, 4, 0, 0]}
            barSize={22}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="latency"
            name="延迟"
            stroke="#52c41a"
            strokeWidth={2}
            dot={false}
          />
          {showErrorRate && (
            <Area
              yAxisId="right"
              type="monotone"
              dataKey="errorRate"
              name="错误率"
              stroke="#f5222d"
              strokeWidth={2}
              fill="rgba(245,34,45,0.15)"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
