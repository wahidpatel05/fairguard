import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Plus, ClipboardCheck, Activity } from 'lucide-react';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import ContractStatusTable from '../components/Common/ContractStatusTable';
import { getProject } from '../api/projects';
import { getAuditLogs } from '../api/audits';

type Tab = 'audits' | 'runtime' | 'receipts';

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('audits');

  const { data: project, isLoading: loadingProject } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  const { data: audits = [], isLoading: loadingAudits } = useQuery({
    queryKey: ['auditLogs', id],
    queryFn: () => getAuditLogs(id!),
    enabled: !!id,
  });

  const domainColors: Record<string, string> = {
    lending: 'bg-blue-100 text-blue-700',
    hiring: 'bg-purple-100 text-purple-700',
    healthcare: 'bg-green-100 text-green-700',
    insurance: 'bg-amber-100 text-amber-700',
    education: 'bg-pink-100 text-pink-700',
    other: 'bg-gray-100 text-gray-600',
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'audits', label: 'Audits' },
    { key: 'runtime', label: 'Runtime' },
    { key: 'receipts', label: 'Receipts' },
  ];

  if (loadingProject) {
    return (
      <AppLayout title="Project Detail">
        <div className="flex justify-center py-20">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout title="Project Detail">
        <div className="text-center py-20 text-gray-500">Project not found.</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title={project.name}>
      <div className="space-y-6">
        {/* Back */}
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Projects
        </button>

        {/* Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-bold text-gray-900">{project.name}</h2>
                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                    domainColors[project.domain?.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {project.domain}
                </span>
              </div>
              {project.description && (
                <p className="text-gray-500 text-sm">{project.description}</p>
              )}
              <p className="text-xs text-gray-400 mt-2">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/audit/new?project=${project.id}`)}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <ClipboardCheck className="w-4 h-4" /> New Audit
              </button>
              <button
                onClick={() => navigate(`/runtime?project=${project.id}`)}
                className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                <Activity className="w-4 h-4" /> Runtime
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div>
          <div className="flex gap-1 border-b border-gray-200 mb-4">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Audits Tab */}
          {activeTab === 'audits' && (
            <div>
              {loadingAudits ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : audits.length === 0 ? (
                <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
                  <p className="text-gray-400 mb-4">No audits yet for this project.</p>
                  <button
                    onClick={() => navigate(`/audit/new?project=${project.id}`)}
                    className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" /> Run First Audit
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-100">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Audit ID', 'Verdict', 'Date', 'Failing Contracts', ''].map((h) => (
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
                        {audits.map((audit) => {
                          const failing = audit.result?.contract_results?.filter(
                            (c) => c.status === 'FAIL'
                          ) ?? [];
                          return (
                            <tr key={audit.id} className="hover:bg-gray-50">
                              <td className="px-5 py-3 text-sm font-mono text-gray-600">
                                {audit.id.slice(0, 8)}…
                              </td>
                              <td className="px-5 py-3">
                                <VerdictBadge verdict={audit.verdict} size="sm" />
                              </td>
                              <td className="px-5 py-3 text-sm text-gray-500">
                                {new Date(audit.created_at).toLocaleString()}
                              </td>
                              <td className="px-5 py-3 text-sm">
                                {failing.length > 0 ? (
                                  <span className="text-red-600 font-medium">{failing.length}</span>
                                ) : (
                                  <span className="text-green-600 font-medium">0</span>
                                )}
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

                  {/* Latest audit contracts */}
                  {audits[0]?.result?.contract_results && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">
                        Latest Audit — Contract Results
                      </h3>
                      <ContractStatusTable contracts={audits[0].result.contract_results} />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Runtime Tab */}
          {activeTab === 'runtime' && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-500 mb-4">View real-time monitoring for this project.</p>
              <button
                onClick={() => navigate(`/runtime?project=${project.id}`)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <Activity className="w-4 h-4" /> Open Runtime Dashboard
              </button>
            </div>
          )}

          {/* Receipts Tab */}
          {activeTab === 'receipts' && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-500 mb-4">View fairness receipts for this project.</p>
              <Link
                to={`/receipts?project=${project.id}`}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                View Receipts
              </Link>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default ProjectDetailPage;
