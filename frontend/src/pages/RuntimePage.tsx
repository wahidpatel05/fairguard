import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import AppLayout from '../components/Layout/AppLayout';
import TrafficLight from '../components/Common/TrafficLight';
import RuntimeTimeSeriesChart from '../components/Charts/RuntimeTimeSeriesChart';
import { getProjects } from '../api/projects';
import { getRuntimeStatus, getRuntimeHistory } from '../api/runtime';

const TIME_WINDOWS = [
  { label: '1 hour', value: '1h' },
  { label: '6 hours', value: '6h' },
  { label: '24 hours', value: '24h' },
  { label: '7 days', value: '7d' },
];

const RuntimePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') ?? '');
  const [endpointId, setEndpointId] = useState('');
  const [timeWindow, setTimeWindow] = useState('1h');

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const { data: status, isLoading: loadingStatus } = useQuery({
    queryKey: ['runtimeStatus', selectedProject, endpointId],
    queryFn: () => getRuntimeStatus(selectedProject, endpointId || undefined),
    enabled: !!selectedProject,
    refetchInterval: 30000,
  });

  const { data: history = [], isLoading: loadingHistory } = useQuery({
    queryKey: ['runtimeHistory', selectedProject, endpointId, timeWindow],
    queryFn: () => getRuntimeHistory(selectedProject, endpointId || undefined, timeWindow),
    enabled: !!selectedProject,
    refetchInterval: 30000,
  });

  const handleProjectChange = (pid: string) => {
    setSelectedProject(pid);
    setSearchParams(pid ? { project: pid } : {});
  };

  const statusBgColors: Record<string, string> = {
    healthy: 'bg-green-50 border-green-200',
    warning: 'bg-amber-50 border-amber-200',
    critical: 'bg-red-50 border-red-200',
  };

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
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Endpoint ID</label>
              <input
                value={endpointId}
                onChange={(e) => setEndpointId(e.target.value)}
                placeholder="All endpoints"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Time Window</label>
              <div className="flex gap-1">
                {TIME_WINDOWS.map((w) => (
                  <button
                    key={w.value}
                    onClick={() => setTimeWindow(w.value)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                      timeWindow === w.value
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
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
            {/* Status Overview */}
            {loadingStatus ? (
              <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-4" />
                <div className="h-8 bg-gray-100 rounded w-1/3" />
              </div>
            ) : status ? (
              <div
                className={`rounded-xl border p-6 ${
                  statusBgColors[status.overall_status] ?? 'bg-white border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Overall Status</p>
                    <TrafficLight status={status.overall_status} size="lg" />
                  </div>
                  <p className="text-xs text-gray-400">
                    Last updated: {new Date(status.last_updated).toLocaleString()}
                  </p>
                </div>

                {status.contract_statuses && status.contract_statuses.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">
                      Contract Statuses
                    </h3>
                    <div className="overflow-x-auto rounded-lg border border-gray-200">
                      <table className="min-w-full divide-y divide-gray-100">
                        <thead className="bg-white/70">
                          <tr>
                            {['Contract', 'Metric', 'Status', 'Current Value', 'Threshold'].map(
                              (h) => (
                                <th
                                  key={h}
                                  className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                >
                                  {h}
                                </th>
                              )
                            )}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50 bg-white/50">
                          {status.contract_statuses.map((cs, i) => (
                            <tr key={`${cs.contract_id}-${i}`}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                {cs.contract_id}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700">{cs.metric}</td>
                              <td className="px-4 py-3">
                                <TrafficLight status={cs.status} showLabel />
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                                {cs.current_value.toFixed(4)}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                                {cs.threshold.toFixed(4)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                No runtime data found. Make sure decisions have been ingested for this project.
              </div>
            )}

            {/* Time Series */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-base font-semibold text-gray-900 mb-4">Metrics Over Time</h3>
              {loadingHistory ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <RuntimeTimeSeriesChart data={history} />
              )}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default RuntimePage;
