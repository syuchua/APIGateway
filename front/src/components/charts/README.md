# 图表组件库

这个目录包含了项目中可复用的图表组件，基于 Recharts 构建。

## 组件列表

### TrafficChart - 流量趋势图
用于显示双线流量数据（入站/出站），支持叠加总量趋势与响应式高度。

```tsx
import { TrafficChart } from '@/components/charts';

const data = [
  { time: '00:00', inbound: 120, outbound: 80 },
  { time: '01:00', inbound: 150, outbound: 100 },
];

<TrafficChart data={data} height={320} showTotal />
```

### ProtocolPieChart - 协议分布饼图
用于显示协议使用分布，默认在中心展示总量并在图例中显示百分比。

```tsx
import { ProtocolPieChart } from '@/components/charts';

const data = [
  { name: 'HTTP', value: 45, color: '#1890ff' },
  { name: 'MQTT', value: 25, color: '#52c41a' },
];

<ProtocolPieChart data={data} height={300} innerRadius={70} outerRadius={110} />
```

### PerformanceBarChart - 性能指标复合图
用于显示吞吐量、延迟以及可选的错误率，多坐标轴组合展示性能指标。

```tsx
import { PerformanceBarChart } from '@/components/charts';

const data = [
  { hour: '00:00', throughput: 500, latency: 20, errorRate: 1.2 },
  { hour: '01:00', throughput: 600, latency: 25, errorRate: 0.8 },
];

<PerformanceBarChart data={data} height={320} showErrorRate />

```

### HealthTrendChart - 系统健康趋势图
用于展示 CPU / 内存利用率与消息速率、错误率的趋势对比。

```tsx
import { HealthTrendChart } from '@/components/charts';

const data = [
  { timestamp: '10:00', cpu: 45, memory: 52, messageRate: 320, errorRate: 0.8 },
  { timestamp: '10:10', cpu: 55, memory: 60, messageRate: 410, errorRate: 0.5 },
];

<HealthTrendChart data={data} height={280} />
```

### MetricLineChart - 指标折线图
用于显示单一指标的时间序列数据。

```tsx
import { MetricLineChart } from '@/components/charts';

const data = [
  { timestamp: '00:00', value: 50, rate: 100 },
  { timestamp: '00:05', value: 65, rate: 120 },
];

<MetricLineChart
  data={data}
  dataKey="value"
  stroke="#52c41a"
  unit=" 个"
  height={300}
/>
```

## 使用场景

- **仪表板页面**: 显示系统整体状态和趋势
- **监控页面**: 实时数据可视化
- **报表页面**: 历史数据分析
- **详情页面**: 特定指标的深入分析

## 设计原则

1. **组件化**: 每个图表都是独立的可复用组件
2. **配置化**: 通过 props 控制图表外观和行为
3. **响应式**: 支持不同屏幕尺寸自适应
4. **一致性**: 统一的视觉风格和交互体验
