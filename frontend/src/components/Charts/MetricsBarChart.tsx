import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { GroupMetric } from '../../types';

interface MetricsBarChartProps {
  data: GroupMetric[];
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

const MetricsBarChart: React.FC<MetricsBarChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return <div className="text-center py-8 text-gray-400">No group metrics available.</div>;
  }

  const chartData = data.map((g) => ({
    group: g.group,
    'Approval Rate': parseFloat(g.approval_rate.toFixed(4)),
    TPR: parseFloat(g.tpr.toFixed(4)),
    FPR: parseFloat(g.fpr.toFixed(4)),
    Accuracy: parseFloat(g.accuracy.toFixed(4)),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="group" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : String(v))} />
        <Legend />
        {['Approval Rate', 'TPR', 'FPR', 'Accuracy'].map((key, i) => (
          <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
};

export default MetricsBarChart;
