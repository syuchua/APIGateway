import { RealtimeMonitoringPanel } from '@/components/business/monitoring/RealtimeMonitoringPanel';
import { RealtimeLogViewer } from '@/components/business/monitoring/RealtimeLogViewer';
import { SystemHealthDashboard } from '@/components/business/monitoring/SystemHealthDashboard';
import { Tabs } from 'antd';

export default function MonitoringPage() {
  const tabItems = [
    {
      key: 'metrics',
      label: '实时监控',
      children: <RealtimeMonitoringPanel />
    },
    {
      key: 'health',
      label: '系统健康',
      children: <SystemHealthDashboard />
    },
    {
      key: 'logs',
      label: '实时日志',
      children: <RealtimeLogViewer />
    }
  ];

  return (
    <div className="space-y-6">
      <Tabs defaultActiveKey="metrics" size="large" items={tabItems} />
    </div>
  );
}