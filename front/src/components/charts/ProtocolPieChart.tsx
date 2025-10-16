'use client';

import React, { useMemo } from 'react';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface ProtocolPieChartProps {
  data: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
}

const renderCenterLabel = (total: number) => () => (
  <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
    <tspan fill="#1f2937" fontSize={18} fontWeight={600}>
      {total}
    </tspan>
    <tspan x="50%" y="50%" dy={22} fill="#9ca3af" fontSize={12}>
      总流量
    </tspan>
  </text>
);

export function ProtocolPieChart({
  data,
  height = 300,
  innerRadius = 70,
  outerRadius = 110
}: ProtocolPieChartProps) {
  const total = useMemo(
    () => data.reduce((sum, item) => sum + item.value, 0),
    [data]
  );

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={4}
            dataKey="value"
            startAngle={90}
            endAngle={-270}
            labelLine={false}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
            {renderCenterLabel(total)()}
          </Pie>
          <Tooltip
            formatter={(value: number, _name, payload) => [
              `${value} (${Math.round((value / total) * 100)}%)`,
              payload?.payload?.name ?? ''
            ]}
          />
          <Legend
            verticalAlign="bottom"
            align="center"
            wrapperStyle={{ paddingTop: 16 }}
            formatter={(value, entry) => {
              const payload = entry?.payload as { value: number } | undefined;
              if (!payload) return value;
              const percent = total > 0 ? Math.round((payload.value / total) * 100) : 0;
              return `${value} · ${payload.value} (${percent}%)`;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
