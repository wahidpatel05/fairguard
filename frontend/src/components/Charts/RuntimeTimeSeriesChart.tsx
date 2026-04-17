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
import type { SnapshotOut } from '../../types';

interface RuntimeTimeSeriesChartProps {
  data: SnapshotOut[];
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const RuntimeTimeSeriesChart: React.FC<RuntimeTimeSeriesChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return <div className="text-center py-8 text-gray-400">No runtime history available.</div>;
  }

  // Pivot snapshots by timestamp, extracting numeric metrics
  const allMetricKeys = Array.from(
    new Set(
      data.flatMap((d) =>
        d.metrics_json
          ? Object.keys(d.metrics_json).filter((k) => typeof d.metrics_json![k] === 'number')
          : [],
      ),
    ),
  );

  const chartData = data
    .slice()
    .reverse()
    .map((d) => {
      const row: Record<string, number | string> = {
        time: new Date(d.evaluated_at).toLocaleTimeString(),
      };
      if (d.metrics_json) {
        for (const key of allMetricKeys) {
          const val = d.metrics_json[key];
          if (typeof val === 'number') row[key] = val;
        }
      }
      return row;
    });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="time" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : String(v))} />
        <Legend />
        {allMetricKeys.map((key, i) => (
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

