'use client';

import React, { useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

interface TrafficChartPoint {
  time: string;
  inbound: number;
  outbound: number;
  total?: number;
}

interface TrafficChartProps {
  data: TrafficChartPoint[];
  height?: number;
  showTotal?: boolean;
}

const formatTooltipValue = (value: number, name: string) => {
  const labelMap: Record<string, string> = {
    inbound: '入站',
    outbound: '出站',
    total: '总量'
  };
  return [`${value.toLocaleString()} MB`, labelMap[name] ?? name];
};

export function TrafficChart({ data, height = 320, showTotal = false }: TrafficChartProps) {
  const enrichedData = useMemo(
    () =>
      data.map((point) => ({
        ...point,
        total: point.total ?? point.inbound + point.outbound
      })),
    [data]
  );

  const maxValue = useMemo(
    () =>
      Math.max(
        10,
        ...enrichedData.flatMap((point) => [point.inbound, point.outbound, point.total ?? 0])
      ),
    [enrichedData]
  );

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <AreaChart data={enrichedData} margin={{ top: 16, right: 24, left: 0, bottom: 8 }}>
          <defs>
            <linearGradient id="inboundGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1890ff" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#1890ff" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="outboundGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#52c41a" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#52c41a" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="time" tickLine={false} />
          <YAxis domain={[0, Math.ceil(maxValue * 1.2)]} tickLine={false} />
          <Tooltip formatter={formatTooltipValue} />
          <Legend />
          <Area
            type="monotone"
            dataKey="inbound"
            name="入站"
            stroke="#1890ff"
            fill="url(#inboundGradient)"
            strokeWidth={2}
            activeDot={{ r: 5 }}
          />
          <Area
            type="monotone"
            dataKey="outbound"
            name="出站"
            stroke="#52c41a"
            fill="url(#outboundGradient)"
            strokeWidth={2}
            activeDot={{ r: 5 }}
          />
          {showTotal && (
            <Line
              type="monotone"
              dataKey="total"
              name="总量"
              stroke="#722ed1"
              strokeDasharray="4 4"
              dot={false}
              strokeWidth={2}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
