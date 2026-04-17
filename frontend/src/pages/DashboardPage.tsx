import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Activity, ClipboardCheck } from 'lucide-react';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import { getProjects } from '../api/projects';
import { getAuditLogs } from '../api/audits';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: projects = [], isLoading: loadingProjects } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });
  const { data: recentAudits = [], isLoading: loadingAudits } = useQuery({
    queryKey: ['allAuditSummaries'],
    queryFn: async () => {
      if (projects.length === 0) return [];
      const results = await Promise.all(projects.map((p) => getAuditLogs(p.id)));
      return results.flat();
    },
    enabled: projects.length > 0,
  });

  const getProjectAudits = (projectId: string) =>
    recentAudits.filter((a) => a.project_id === projectId);

  const getLatestVerdict = (projectId: string) => {
    const projectAudits = getProjectAudits(projectId);
    if (projectAudits.length === 0) return null;
    return projectAudits.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0].verdict;
  };

  const domainColors: Record<string, string> = {
    lending: 'bg-blue-100 text-blue-700',
    hiring: 'bg-purple-100 text-purple-700',
    healthcare: 'bg-green-100 text-green-700',
    insurance: 'bg-amber-100 text-amber-700',
    education: 'bg-pink-100 text-pink-700',
  };

  const failingAudits = recentAudits.filter((a) => a.verdict === 'FAIL').length;

  return (
    <AppLayout title="Dashboard">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <p className="text-sm text-gray-500">Total Projects</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{projects.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <p className="text-sm text-gray-500">Total Audits</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{recentAudits.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <p className="text-sm text-gray-500">Failing Audits</p>
            <p className="text-3xl font-bold text-red-600 mt-1">{failingAudits}</p>
          </div>
        </div>

        {/* Projects */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Projects</h2>
            <Link
              to="/projects"
              className="text-sm text-blue-600 hover:underline font-medium"
            >
              View all
            </Link>
          </div>

          {loadingProjects || loadingAudits ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-2/3 mb-3" />
                  <div className="h-3 bg-gray-100 rounded w-1/3" />
                </div>
              ))}
            </div>
          ) : projects.length === 0 ? (
            <div className="bg-white rounded-xl border border-dashed border-gray-300 p-10 text-center">
              <p className="text-gray-400 mb-4">No projects yet.</p>
              <Link
                to="/projects"
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" /> Create Project
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {projects.map((project) => {
                const verdict = getLatestVerdict(project.id);
                const projectAudits = getProjectAudits(project.id);

                return (
                  <div
                    key={project.id}
                    className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-gray-900 text-base">{project.name}</h3>
                        <span
                          className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                            domainColors[project.domain?.toLowerCase()] ??
                            'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {project.domain}
                        </span>
                      </div>
                      {verdict && <VerdictBadge verdict={verdict} size="sm" />}
                    </div>

                    <div className="text-sm text-gray-500 mb-4">
                      <span className="font-medium text-gray-700">{projectAudits.length}</span>{' '}
                      audit{projectAudits.length !== 1 ? 's' : ''}
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={() => navigate(`/audit/new?project=${project.id}`)}
                        className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 px-3 py-2 rounded-lg font-medium transition-colors"
                      >
                        <ClipboardCheck className="w-3.5 h-3.5" />
                        New Audit
                      </button>
                      <button
                        onClick={() => navigate(`/runtime?project=${project.id}`)}
                        className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-gray-50 text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg font-medium transition-colors"
                      >
                        <Activity className="w-3.5 h-3.5" />
                        Runtime
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Audits */}
        {recentAudits.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Audits</h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    {['Project', 'File', 'Verdict', 'Date', ''].map((h) => (
                      <th
                        key={h}
                        className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {recentAudits.slice(0, 5).map((audit) => {
                    const project = projects.find((p) => p.id === audit.project_id);
                    return (
                      <tr key={audit.id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-sm text-gray-900">
                          {project?.name ?? audit.project_id}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-500 max-w-xs truncate">
                          {audit.dataset_filename ?? '—'}
                        </td>
                        <td className="px-5 py-3">
                          <VerdictBadge verdict={audit.verdict ?? 'UNKNOWN'} size="sm" />
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-500">
                          {new Date(audit.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Link
                            to={`/audit/${audit.id}`}
                            className="text-sm text-blue-600 hover:underline"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default DashboardPage;
