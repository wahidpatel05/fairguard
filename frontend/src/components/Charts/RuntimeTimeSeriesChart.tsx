import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { RuntimeHistoryPoint } from '../../api/runtime';

interface RuntimeTimeSeriesChartProps {
  data: RuntimeHistoryPoint[];
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const RuntimeTimeSeriesChart: React.FC<RuntimeTimeSeriesChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return <div className="text-center py-8 text-gray-400">No runtime history available.</div>;
  }

  // Pivot data by timestamp
  const metricKeys = Array.from(new Set(data.map((d) => d.metric)));
  const byTime = data.reduce<Record<string, Record<string, number | string>>>((acc, d) => {
    const ts = new Date(d.timestamp).toLocaleTimeString();
    if (!acc[ts]) acc[ts] = { time: ts };
    acc[ts][d.metric] = parseFloat(d.value.toFixed(4));
    return acc;
  }, {});

  const chartData = Object.values(byTime);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="time" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : String(v))} />
        <Legend />
        {metricKeys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={COLORS[i % COLORS.length]}
            dot={false}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};

export default RuntimeTimeSeriesChart;
