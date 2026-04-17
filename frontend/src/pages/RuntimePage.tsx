import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import AppLayout from '../components/Layout/AppLayout';
import TrafficLight from '../components/Common/TrafficLight';
import { getProjects } from '../api/projects';
import { getRuntimeStatus, getRuntimeSnapshots } from '../api/runtime';
import type { RuntimeWindowStatus } from '../types';
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

const WINDOW_LABELS: Record<string, string> = {
  '1h': '1 Hour',
  '6h': '6 Hours',
  '24h': '24 Hours',
  '7d': '7 Days',
};

const statusColors: Record<string, string> = {
  healthy: 'bg-green-50 border-green-200',
  warning: 'bg-amber-50 border-amber-200',
  critical: 'bg-red-50 border-red-200',
  insufficient_data: 'bg-gray-50 border-gray-200',
  no_data: 'bg-gray-50 border-gray-200',
};

const WindowCard: React.FC<{ windowType: string; data: RuntimeWindowStatus }> = ({
  windowType,
  data,
}) => {
  const label = WINDOW_LABELS[windowType] ?? windowType;
  const metricEntries = Object.entries(data.metrics).filter(
    ([, v]) => typeof v === 'number',
  ) as [string, number][];

  return (
    <div className={`rounded-xl border p-5 ${statusColors[data.status] ?? 'bg-white border-gray-200'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{label} window</h3>
        <TrafficLight status={data.status} size="sm" showLabel />
      </div>
      <p className="text-xs text-gray-400 mb-3">
        {data.count} decision{data.count !== 1 ? 's' : ''}
        {data.evaluated_at
          ? ` · ${new Date(data.evaluated_at).toLocaleTimeString()}`
          : ''}
      </p>
      {metricEntries.length > 0 ? (
        <dl className="space-y-1.5">
          {metricEntries.map(([key, val]) => (
            <div key={key} className="flex justify-between text-xs">
              <dt className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</dt>
              <dd className="font-mono font-medium text-gray-900">
                {typeof val === 'number' ? val.toFixed(4) : String(val)}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-xs text-gray-400">No metrics computed yet.</p>
      )}
    </div>
  );
};

const SNAPSHOT_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const RuntimePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') ?? '');
  const [aggregationKey, setAggregationKey] = useState('');

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const { data: statusData, isLoading: loadingStatus } = useQuery({
    queryKey: ['runtimeStatus', selectedProject, aggregationKey],
    queryFn: () => getRuntimeStatus(selectedProject, aggregationKey || undefined),
    enabled: !!selectedProject,
    refetchInterval: 30000,
  });

  const { data: snapshots = [], isLoading: loadingSnapshots } = useQuery({
    queryKey: ['runtimeSnapshots', selectedProject, aggregationKey],
    queryFn: () => getRuntimeSnapshots(selectedProject, aggregationKey || undefined, 50),
    enabled: !!selectedProject,
    refetchInterval: 30000,
  });

  const handleProjectChange = (pid: string) => {
    setSelectedProject(pid);
    setSearchParams(pid ? { project: pid } : {});
  };

  // Build chart data from snapshots
  const chartData = snapshots
    .slice()
    .reverse()
    .map((s) => {
      const ts = new Date(s.evaluated_at).toLocaleTimeString();
      const metrics: Record<string, number | string> = { time: ts, window: s.window_type };
      if (s.metrics_json) {
        for (const [k, v] of Object.entries(s.metrics_json)) {
          if (typeof v === 'number') metrics[k] = v;
        }
      }
      return metrics;
    });

  const metricKeys = Array.from(
    new Set(
      chartData.flatMap((d) =>
        Object.keys(d).filter((k) => k !== 'time' && k !== 'window'),
      ),
    ),
  );

  return (
    <AppLayout title="Runtime Monitoring">
      <div className="space-y-6">
        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Project</label>
              <select
                value={selectedProject}
                onChange={(e) => handleProjectChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-48"
              >
                <option value="">Select project…</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Aggregation Key
              </label>
              <input
                value={aggregationKey}
                onChange={(e) => setAggregationKey(e.target.value)}
                placeholder="Optional endpoint / model key"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {!selectedProject && (
          <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center text-gray-400">
            Select a project to view runtime monitoring data.
          </div>
        )}

        {selectedProject && (
          <>
            {/* Overall Status */}
            {loadingStatus ? (
              <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-4" />
                <div className="h-8 bg-gray-100 rounded w-1/3" />
              </div>
            ) : statusData ? (
              <div
                className={`rounded-xl border p-6 ${
                  statusColors[statusData.overall_status] ?? 'bg-white border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Overall Status</p>
                    <TrafficLight status={statusData.overall_status} size="lg" />
                  </div>
                </div>

                {/* Window cards */}
                {Object.keys(statusData.windows).length > 0 && (
                  <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                    {Object.entries(statusData.windows).map(([wt, wdata]) => (
                      <WindowCard key={wt} windowType={wt} data={wdata} />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                No runtime data found. Make sure decisions have been ingested for this project.
              </div>
            )}

            {/* Snapshots Time Series */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-base font-semibold text-gray-900 mb-4">
                Metrics History (Snapshots)
              </h3>
              {loadingSnapshots ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : chartData.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  No snapshot history available yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(v) => (typeof v === 'number' ? v.toFixed(4) : String(v))}
                    />
                    <Legend />
                    {metricKeys.map((key, i) => (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={SNAPSHOT_COLORS[i % SNAPSHOT_COLORS.length]}
                        dot={false}
                        strokeWidth={2}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default RuntimePage;
